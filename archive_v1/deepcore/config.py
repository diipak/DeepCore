import os
import shutil
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

class Settings:
    def __init__(self):
        env_db_path = os.getenv("DEEPCORE_DB_PATH")
        if env_db_path:
            self.DB_PATH = env_db_path
        else:
            # Default to stable ~/.deepcore/deepcore.db
            home_dir = os.path.expanduser("~/.deepcore")
            target_db = os.path.join(home_dir, "deepcore.db")
            
            # If an old local deepcore.db exists, migrate it once
            old_local_db = "deepcore.db"
            if os.path.exists(old_local_db):
                # Never overwrite existing ~/.deepcore/deepcore.db
                if not os.path.exists(target_db):
                    os.makedirs(home_dir, exist_ok=True)
                    try:
                        shutil.copy2(old_local_db, target_db)
                        print(f"DeepCore Migration: Found local database at '{os.path.abspath(old_local_db)}'. Migrated to '{target_db}'.")
                    except Exception as e:
                        print(f"DeepCore Migration Error: Failed to migrate local database: {e}")
                else:
                    # Target already exists, do not overwrite
                    pass
            else:
                os.makedirs(home_dir, exist_ok=True)
                
            self.DB_PATH = target_db
    
        # Local LLM (Ollama) settings for the Conversation Runtime.
        # Overridable via .env or environment variables; defaults assume a
        # local `ollama serve` instance on the default port.
        self.OLLAMA_HOST = os.getenv("DEEPCORE_OLLAMA_HOST", "http://localhost:11434")
        self.OLLAMA_MODEL = os.getenv("DEEPCORE_OLLAMA_MODEL", "gemma4:12b")
        self.OLLAMA_TIMEOUT_SECONDS = float(os.getenv("DEEPCORE_OLLAMA_TIMEOUT", "60"))

    @property
    def DATABASE_URL(self) -> str:
        return f"sqlite:///{self.DB_PATH}"

settings = Settings()

