from pydantic import BaseModel, Field

class File(BaseModel):
    """
    Semantic Contract Object Model representing a generic file on disk.
    Contains only platform-agnostic, filesystem-level metadata.
    """
    absolute_path: str = Field(..., description="Absolute file path on disk")
    relative_path: str = Field(..., description="Relative file path from the root directory")
    filename: str = Field(..., description="Filename including extension")
    file_size: int = Field(..., description="Size of file in bytes")
    created_at_ts: float = Field(..., description="Epoch timestamp of file creation")
    modified_at_ts: float = Field(..., description="Epoch timestamp of last modification")
    parent_folder: str = Field(..., description="Immediate parent directory name")


class Folder(BaseModel):
    """
    Semantic Contract Object Model representing a directory.
    """
    absolute_path: str = Field(..., description="Absolute folder path on disk")
    relative_path: str = Field(..., description="Relative folder path from the root directory")
    created_at_ts: float = Field(..., description="Epoch timestamp of folder creation")
