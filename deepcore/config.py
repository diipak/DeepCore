import os
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

class Settings:
    DB_PATH: str = os.getenv("DEEPCORE_DB_PATH", "deepcore.db")
    
    @property
    def DATABASE_URL(self) -> str:
        return f"sqlite:///{self.DB_PATH}"

settings = Settings()
