"""
Grounded prompt construction engine for DeepCore.

Combines deterministic context from ContextEngine, full-text note body
snippets from ContentService, and recent conversation history into a bounded,
grounded prompt for local LLM inference.
"""
from typing import List, Optional
from deepcore2.intelligence.context_engine import ContextPackage
from deepcore2.core.content.service import ContentService
from deepcore2.storage.sqlite.models import Message as DBMessage

MAX_CONTENT_SNIPPET_CHARS = 1500
MAX_CONTENT_SEARCH_MATCHES = 5
MAX_HISTORY_MESSAGES = 8
MAX_HISTORY_CHARS = 2000

SYSTEM_PREAMBLE = (
    "You are DeepCore, the user's private personal-knowledge and homelab intelligence assistant. "
    "Answer using the context below, which contains verified homelab memories and captured notes. "
    "If the context does not contain enough information to answer, you should utilize your available tools "
    "(such as web search for public/current topics or filesystem tools for local notes and files). "
    "Only say you do not have enough information if the answer cannot be found in the context or via your available tools."
)


class GroundedPromptBuilder:
    """
    Constructs a bounded, grounded prompt incorporating deterministic context,
    full-text note body snippets, cross-agent OpenMemory facts, and recent conversation history.
    """

    def build_prompt(
        self,
        query: str,
        context_package: Optional[ContextPackage],
        content_service: ContentService,
        history_messages: Optional[List[DBMessage]] = None,
        openmemory_blocks: Optional[List[str]] = None,
    ) -> str:
        sections = []

        # 0. OpenMemory Cross-Agent Semantic Memories (if present)
        if openmemory_blocks:
            sections.append("## Core Homelab & Identity Memories\n" + "\n\n".join(openmemory_blocks))

        # 1. Memories found via ContextEngine & ContentService search
        cited_uuids = set()
        memory_blocks = []

        if context_package and context_package.memories:
            for ctx_memory in context_package.memories:
                ref = ctx_memory.memory
                cited_uuids.add(ref.uuid)
                content_entry = content_service.get_content(ref.uuid)
                snippet = ""
                if content_entry and content_entry.raw_text:
                    snippet = content_entry.raw_text[:MAX_CONTENT_SNIPPET_CHARS]
                elif ref.description:
                    snippet = ref.description
                memory_blocks.append(
                    f"### {ref.title} ({ref.object_type}, source: {ref.source_system})\n{snippet or '(no indexed content)'}"
                )

        # Full-text body search for matches missed by title/description search
        for db_obj, content_idx in content_service.search_content(query)[:MAX_CONTENT_SEARCH_MATCHES]:
            if db_obj.uuid in cited_uuids:
                continue
            cited_uuids.add(db_obj.uuid)
            snippet = (content_idx.raw_text or "")[:MAX_CONTENT_SNIPPET_CHARS]
            memory_blocks.append(
                f"### {db_obj.title} ({db_obj.object_type}, source: {db_obj.source_system})\n{snippet or '(no indexed content)'}"
            )

        if memory_blocks:
            sections.append("## Relevant notes\n" + "\n\n".join(memory_blocks))

        if context_package and context_package.concepts:
            concept_titles = ", ".join(c.concept.title for c in context_package.concepts)
            sections.append(f"## Related concepts\n{concept_titles}")

        if not memory_blocks and not openmemory_blocks and (not context_package or not context_package.concepts):
            sections.append(
                "## Relevant context\n(No matching notes or memories were found in the registry for this query.)"
            )

        context_block = "\n\n".join(sections)

        # 2. Recent Conversation History
        history_block = ""
        if history_messages:
            # Take up to MAX_HISTORY_MESSAGES recent messages
            recent_msgs = history_messages[-MAX_HISTORY_MESSAGES:]
            history_lines = []
            char_count = 0
            for msg in reversed(recent_msgs):
                line = f"{msg.role.capitalize()}: {msg.content}"
                if char_count + len(line) > MAX_HISTORY_CHARS:
                    break
                history_lines.insert(0, line)
                char_count += len(line)

            if history_lines:
                history_block = "## Recent Conversation\n" + "\n".join(history_lines) + "\n\n"

        return (
            f"{SYSTEM_PREAMBLE}\n\n"
            f"{context_block}\n\n"
            f"{history_block}"
            f"## Question\n{query}\n\n"
            f"## Answer\n"
        )
