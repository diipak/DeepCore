from enum import Enum
from typing import List, Dict, Any, Optional, Protocol, runtime_checkable
from pydantic import BaseModel, Field

class DescriptorCategory(str, Enum):
    """Strongly typed categories of executable capabilities in DeepCore."""
    TOOL = "tool"
    SKILL = "skill"
    PROVIDER = "provider"
    CONVERSATION = "conversation"
    PROMPT = "prompt"
    MODEL = "model"


class BaseDescriptor(BaseModel):
    """
    Immutable metadata descriptor model shared across all DeepCore capabilities.
    Configured as frozen (immutable) to prevent modification during runtime.
    """
    id: str = Field(
        ...,
        description="Globally unique and stable identifier for the capability."
    )
    name: str = Field(
        ...,
        description="Human-readable name of the capability."
    )
    description: str = Field(
        ...,
        description="Detailed description of what the capability does."
    )
    category: DescriptorCategory = Field(
        ...,
        description="Strongly-typed category class of the capability."
    )
    descriptor_version: str = Field(
        "1.0.0",
        description="Version string of the descriptor schema contract."
    )
    implementation_version: str = Field(
        "1.0.0",
        description="Component release version of the underlying executable implementation."
    )
    enabled: bool = Field(
        True,
        description="Flags whether this capability is currently active and executable."
    )
    configurable: bool = Field(
        False,
        description="Declares if this capability requires runtime configuration parameters."
    )
    experimental: bool = Field(
        False,
        description="Flags if this capability is considered experimental or preview-only."
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Advisory tags for categorizing and filtering capabilities. Never influences execution."
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Advisory arbitrary key-value metadata dictionary. Never influences execution."
    )

    model_config = {
        "frozen": True  # Enforce descriptor immutability at execution time
    }


@runtime_checkable
class DescriptorProvider(Protocol):
    """
    Lightweight protocol for self-describing runtime components.
    Any class exposing descriptors must satisfy this protocol.
    """
    def get_descriptor(self) -> BaseDescriptor:
        """Returns the stable, self-describing metadata descriptor for the component."""
        ...


class ProviderDescriptor(BaseDescriptor):
    """Descriptor metadata schema for ingestion and sync Providers."""
    provider_type: str = Field(
        ...,
        description="Ingestion/Sync provider type (e.g. 'markdown', 'youtube')."
    )
    supported_formats: List[str] = Field(
        default_factory=list,
        description="List of file extensions or media formats supported by the provider."
    )


class PromptDescriptor(BaseDescriptor):
    """Descriptor metadata schema for Prompt templates and orchestration structures."""
    template_identifier: str = Field(
        ...,
        description="Stable key identifying the prompt template string."
    )
    strategy_name: str = Field(
        ...,
        description="Name of the prompt strategy (e.g. 'few_shot', 'cot')."
    )
    input_variables: List[str] = Field(
        default_factory=list,
        description="List of expected input variable names for template formatting."
    )


class ModelDescriptor(BaseDescriptor):
    """Descriptor metadata schema for offline and online AI models."""
    model_type: str = Field(
        ...,
        description="Underlying model type (e.g. 'local_llm', 'embedding', 'rerank')."
    )
    context_length: int = Field(
        ...,
        description="Maximum input token context length supported by the model."
    )
    publisher: str = Field(
        ...,
        description="Entity that published/released the model weights."
    )
