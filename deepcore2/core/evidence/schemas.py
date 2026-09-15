from typing import List, Optional
from pydantic import BaseModel

class Evidence(BaseModel):
    source_uuid: str
    target_uuid: str
    relationship_path: List[str]
    reason: str
    confidence: Optional[float] = 1.0
