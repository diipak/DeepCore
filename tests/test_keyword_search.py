import pytest
from deepcore.core.utils.text import extract_search_keywords
from deepcore.core.registry.service import RegistryService
from deepcore.core.content.service import ContentService
from deepcore.core.objects.schemas import RegistryObjectCreate, ObjectType
from deepcore.intelligence import ContextRequest, ContextEngine
from deepcore.intelligence.grounding import GroundedPromptBuilder

def test_extract_search_keywords():
    """Verify natural-language query tokenization and stopword removal."""
    # Real failure case from problem statement
    kw1 = extract_search_keywords("Share the information about AI")
    assert kw1 == ["ai"]

    # Complex question
    kw2 = extract_search_keywords("How do I setup Docker on macOS?")
    assert kw2 == ["setup", "docker", "macos"]

    # Deduplication check
    kw3 = extract_search_keywords("AI and AI development")
    assert kw3 == ["ai", "development"]

    # Fallback when all tokens are stop words
    kw4 = extract_search_keywords("What is it?")
    assert len(kw4) > 0  # Should fall back to non-empty tokens

def test_natural_language_search_objects(db_session):
    """Verify RegistryService.search_objects retrieves target note with natural language phrasing."""
    service = RegistryService(db_session)
    
    # Register target note
    note = service.register_object(RegistryObjectCreate(
        object_type=ObjectType.NOTE,
        title="AI System Overview",
        source_system="obsidian",
        location="/notes/ai.md",
        description="Comprehensive notes about artificial intelligence",
        status="active"
    ))

    # Search with full natural language prompt
    results = service.search_objects(query="Share the information about AI")
    assert len(results) == 1
    assert results[0].id == note.id

def test_natural_language_search_content(db_session):
    """Verify ContentService.search_content retrieves indexed content with natural language phrasing."""
    reg_service = RegistryService(db_session)
    content_service = ContentService(db_session)

    note = reg_service.register_object(RegistryObjectCreate(
        object_type=ObjectType.NOTE,
        title="Machine Learning Principles",
        source_system="obsidian",
        location="/notes/ml.md",
        status="active"
    ))
    
    from deepcore.storage.sqlite.models import ContentIndex as DBContentIndex
    content_idx = DBContentIndex(
        object_id=note.id,
        content_type="text/markdown",
        raw_text="This document covers neural networks and deep learning concepts in modern AI.",
        content_hash="hash123"
    )
    db_session.add(content_idx)
    db_session.commit()

    results = content_service.search_content(query="Can you explain the concepts of AI?")
    assert len(results) == 1
    assert results[0][0].id == note.id

def test_natural_language_grounding_context(db_session):
    """Verify assistant grounding builds relevant context when asked a natural language question."""
    reg_service = RegistryService(db_session)
    content_service = ContentService(db_session)

    note = reg_service.register_object(RegistryObjectCreate(
        object_type=ObjectType.NOTE,
        title="Artificial Intelligence Architecture",
        source_system="obsidian",
        location="/notes/ai_arch.md",
        status="active"
    ))
    
    from deepcore.storage.sqlite.models import ContentIndex as DBContentIndex
    content_idx = DBContentIndex(
        object_id=note.id,
        content_type="text/markdown",
        raw_text="Deep learning architectures rely on multi-layer neural networks.",
        content_hash="hash456"
    )
    db_session.add(content_idx)
    db_session.commit()

    prompt = "Share the information about AI"
    engine = ContextEngine(db_session)
    context_pkg = engine.build_context(ContextRequest(query=prompt))
    grounded_prompt = GroundedPromptBuilder().build_prompt(
        query=prompt,
        context_package=context_pkg,
        content_service=content_service
    )

    assert "Artificial Intelligence Architecture" in grounded_prompt
    assert "Deep learning architectures rely on multi-layer neural networks" in grounded_prompt
