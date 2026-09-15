"""
Interactive CLI runner to test DeepCore 2.0 ConversationService and OpenMemory grounding.
"""
import time
from deepcore2.core.assistant.service import ConversationService
from deepcore2.storage.sqlite.db import get_db


def main():
    print("=" * 65)
    print("🧠 DeepCore 2.0 — Interactive Grounding & Memory Test Bench")
    print("=" * 65)
    print("Initializing ConversationService & connecting to local services...")

    db = next(get_db())
    try:
        service = ConversationService(db=db, workspace_id=1)
        session = service.start_session("CONTINUE_THINKING")
        print(f"Session UUID: {session.session_uuid}")
        print(f"Assistant: {session.messages[0].content}\n")
        print("Type your question below (or 'exit' / 'quit' to end):")
        print("-" * 65)

        while True:
            try:
                user_input = input("\nYou > ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\nExiting.")
                break

            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit", "q"):
                print("Session ended.")
                break

            start_t = time.time()
            state = service.post_message(session.session_uuid, user_input)
            elapsed = time.time() - start_t

            assistant_msg = state.messages[-1]

            print(f"\nDeepCore ({elapsed:.2f}s) >")
            print(assistant_msg.content)

            if assistant_msg.evidence:
                print("\n[Evidential Citations & Memories Grounded]:")
                for ev in assistant_msg.evidence:
                    print(f"  • [{ev.source_uuid}] ({','.join(ev.relationship_path)}): {ev.reason}")
            else:
                print("\n[Evidential Citations]: (No notes or memories cited)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
