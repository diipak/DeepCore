import os
import shutil
import sys
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

class Settings:
    def __init__(self):
        env_db_path = os.getenv("DEEPCORE_DB_PATH")
        if env_db_path:
            self.DB_PATH = env_db_path
        else:
            # Default to stable ~/.deepcore2/deepcore2.db
            home_dir = os.path.expanduser("~/.deepcore2")
            target_db = os.path.join(home_dir, "deepcore2.db")
            
            # If an old local deepcore2.db exists, migrate it once
            old_local_db = "deepcore2.db"
            if os.path.exists(old_local_db):
                # Never overwrite existing ~/.deepcore2/deepcore2.db
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
        self.OLLAMA_TIMEOUT_SECONDS = float(os.getenv("DEEPCORE_OLLAMA_TIMEOUT", "120"))

        # OpenMemory integration settings
        self.OPENMEMORY_HOST = os.getenv("DEEPCORE_OPENMEMORY_HOST", "http://127.0.0.1:8765")
        self.OPENMEMORY_USER_ID = os.getenv("DEEPCORE_OPENMEMORY_USER_ID", os.getenv("USER", "default_user"))
        self.OPENMEMORY_TIMEOUT_SECONDS = float(os.getenv("DEEPCORE_OPENMEMORY_TIMEOUT", "2.0"))
        self.OPENMEMORY_DEFAULT_CATEGORIES = ["infrastructure", "coding", "automation", "preferences", "general"]
        self.OPENMEMORY_EXCLUDED_NAMESPACES = ["personal_finz", "personalfin", "poojamusic", "algomirror", "career"]

        # Local Audio Subsystem (STT / TTS) settings
        self.AUDIO_STT_BACKEND = os.getenv("DEEPCORE_AUDIO_STT_BACKEND", "auto")
        self.AUDIO_STT_MODEL = os.getenv("DEEPCORE_AUDIO_STT_MODEL", "mlx-community/whisper-base.en-mlx")
        self.AUDIO_TTS_VOICE = os.getenv("DEEPCORE_AUDIO_TTS_VOICE", "af_bella")
        self.AUDIO_TTS_SPEED = float(os.getenv("DEEPCORE_AUDIO_TTS_SPEED", "1.05"))
        self.AUDIO_SAMPLE_RATE = int(os.getenv("DEEPCORE_AUDIO_SAMPLE_RATE", "24000"))

        # Knowledge Vault (Obsidian) paths
        self.VAULT_ROOT = os.path.realpath(os.path.expanduser(os.getenv("DEEPCORE_VAULT_ROOT", "~/Documents/Notes")))
        self.VAULT_AI_DIR = os.path.realpath(os.path.expanduser(os.getenv("DEEPCORE_VAULT_AI_DIR", "~/Documents/Notes/AI")))

        # External MCP Tool Integrations (Invariant #8)
        self.BRAVE_API_KEY = os.getenv("BRAVE_API_KEY", "")
        self.BRAVE_MCP_COMMAND = os.getenv("DEEPCORE_BRAVE_MCP_COMMAND", "npx -y @modelcontextprotocol/server-brave-search")

        # DuckDuckGo MCP (Zero API key web search)
        self.MCP_DUCKDUCKGO_ENABLED = os.getenv("DEEPCORE_MCP_DUCKDUCKGO_ENABLED", "true").lower() in ("true", "1", "yes")
        self.MCP_DUCKDUCKGO_COMMAND = os.getenv("DEEPCORE_MCP_DUCKDUCKGO_COMMAND", f"{sys.executable} -m deepcore2.runtime.tools.mcp_servers.ddg_server")

        # Jailed Filesystem MCP (Read-only vault exploration)
        self.MCP_FILESYSTEM_ENABLED = os.getenv("DEEPCORE_MCP_FILESYSTEM_ENABLED", "true").lower() in ("true", "1", "yes")
        self.MCP_FILESYSTEM_ROOT = os.path.realpath(os.path.expanduser(os.getenv("DEEPCORE_MCP_FILESYSTEM_ROOT", self.VAULT_ROOT)))
        self.MCP_FILESYSTEM_COMMAND = os.getenv("DEEPCORE_MCP_FILESYSTEM_COMMAND", f"npx -y @modelcontextprotocol/server-filesystem {self.MCP_FILESYSTEM_ROOT}")

        # YouTube Ingestion Settings
        self.YOUTUBE_DEEPCORE_PLAYLIST_URL = os.getenv("YOUTUBE_DEEPCORE_PLAYLIST_URL", "")
        self.YOUTUBE_CAPTURES_DIR = os.getenv(
            "DEEPCORE_YOUTUBE_CAPTURES_DIR",
            os.path.join(self.VAULT_AI_DIR, "Captures", "YouTube")
        )

    @property
    def DATABASE_URL(self) -> str:
        return f"sqlite:///{self.DB_PATH}"

settings = Settings()

