import pytest
import json
from pydantic import ValidationError

from deepcore.runtime.descriptors import (
    DescriptorCategory,
    BaseDescriptor,
    DescriptorProvider,
    ProviderDescriptor,
    PromptDescriptor,
    ModelDescriptor
)
from deepcore.runtime.tools.base import ToolDescriptor, BaseTool, ToolRequest, ToolResult, ToolDiagnostics, ToolStatus
from deepcore.runtime.skills.base import SkillDescriptor, BaseSkill, SkillRequest, SkillResult, SkillDiagnostics, SkillStatus
from deepcore.runtime.conversation.base import ConversationDescriptor, ConversationMode


# ==========================================
# Mock Implementations for Protocol Check
# ==========================================

class MockTool(BaseTool):
    name = "mock_tool"
    description = "A mock tool for testing descriptors"
    category = "Query"
    input_schema = type("In", (), {"model_json_schema": lambda: {}})
    output_schema = type("Out", (), {"model_json_schema": lambda: {}})
    
    def execute(self, request: ToolRequest) -> ToolResult:
        return ToolResult(
            request_id=request.request_id,
            status=ToolStatus.SUCCESS,
            outputs={},
            diagnostics=ToolDiagnostics(execution_time_ms=0.0)
        )


class MockSkill(BaseSkill):
    name = "mock_skill"
    description = "A mock skill for testing descriptors"
    input_schema = type("In", (), {"model_json_schema": lambda: {}})
    output_schema = type("Out", (), {"model_json_schema": lambda: {}})
    
    def execute(self, request: SkillRequest) -> SkillResult:
        return SkillResult(
            request_id=request.request_id,
            status=SkillStatus.SUCCESS,
            outputs={},
            diagnostics=SkillDiagnostics(execution_time_ms=0.0)
        )


# ==========================================
# Test Cases
# ==========================================

def test_descriptor_inheritance():
    # Verify that ToolDescriptor and SkillDescriptor inherit from BaseDescriptor
    assert issubclass(ToolDescriptor, BaseDescriptor)
    assert issubclass(SkillDescriptor, BaseDescriptor)
    assert issubclass(ConversationDescriptor, BaseDescriptor)
    assert issubclass(ProviderDescriptor, BaseDescriptor)
    assert issubclass(PromptDescriptor, BaseDescriptor)
    assert issubclass(ModelDescriptor, BaseDescriptor)


def test_descriptor_protocol_compliance():
    # Verify our mock implementations satisfy get_descriptor
    tool_inst = MockTool()
    skill_inst = MockSkill()
    
    # Check they can compile a descriptor
    tool_desc = tool_inst.get_descriptor()
    skill_desc = skill_inst.get_descriptor()
    
    assert isinstance(tool_desc, BaseDescriptor)
    assert isinstance(skill_desc, BaseDescriptor)
    
    assert tool_desc.category == DescriptorCategory.TOOL
    assert skill_desc.category == DescriptorCategory.SKILL


def test_descriptor_immutability():
    # Descriptors must be immutable (frozen=True)
    desc = BaseDescriptor(
        id="test-imm",
        name="Immutability Test",
        description="Verify descriptors cannot be modified",
        category=DescriptorCategory.TOOL
    )
    
    with pytest.raises(ValidationError):
        # In Pydantic v2, mutating a frozen model field raises ValidationError
        desc.name = "Mutated Name"


def test_json_roundtrip_serialization():
    # Round-trip JSON serialization should preserve all attributes deterministically
    desc = ProviderDescriptor(
        id="markdown_provider",
        name="Markdown Sync Provider",
        description="Ingests local markdown directories",
        category=DescriptorCategory.PROVIDER,
        provider_type="markdown",
        supported_formats=[".md", ".markdown"]
    )
    
    serialized = desc.model_dump_json()
    deserialized = ProviderDescriptor.model_validate_json(serialized)
    
    assert deserialized.id == desc.id
    assert deserialized.name == desc.name
    assert deserialized.category == desc.category
    assert deserialized.provider_type == desc.provider_type
    assert deserialized.supported_formats == desc.supported_formats


def test_stable_descriptor_ids():
    # Verification that default get_descriptor() populates id with self.name as a stable fallback
    tool = MockTool()
    desc = tool.get_descriptor()
    assert desc.id == "mock_tool"
    
    # Custom custom ID specification should be preserved
    tool.id = "custom-id-123"
    desc_custom = tool.get_descriptor()
    assert desc_custom.id == "custom-id-123"


def test_prompt_descriptor_metadata():
    # PromptDescriptor does not contain template body, only metadata descriptors
    prompt_desc = PromptDescriptor(
        id="sync_prompt",
        name="Sync Guidance Prompt",
        description="Provides instructions on note synchronization",
        category=DescriptorCategory.PROMPT,
        template_identifier="sync_vault_v1",
        strategy_name="zero_shot",
        input_variables=["vault_path", "notes_count"]
    )
    
    assert prompt_desc.template_identifier == "sync_vault_v1"
    assert prompt_desc.strategy_name == "zero_shot"
    assert "vault_path" in prompt_desc.input_variables


def test_version_validation():
    # Verify validation of default version fields
    desc = ModelDescriptor(
        id="embedding_model",
        name="MiniLM Embedding",
        description="Local semantic embedding engine",
        category=DescriptorCategory.MODEL,
        model_type="embedding",
        context_length=512,
        publisher="sentence-transformers",
        descriptor_version="2.0.0",
        implementation_version="1.2.3"
    )
    
    assert desc.descriptor_version == "2.0.0"
    assert desc.implementation_version == "1.2.3"
