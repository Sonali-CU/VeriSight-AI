from pydantic import BaseModel
from typing import Literal, Optional

class HealthResponse(BaseModel):
    status: str
    service: str
    model_status: str

class ModelStatus(BaseModel):
    modality: Literal["image", "video", "audio", "fusion"]
    status: str
    architecture: Optional[str] = None
    weights_path: Optional[str] = None
    note: str
