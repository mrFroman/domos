from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class LawyerRequest:
    user_id: int
    lawyer_id: int
    request_type: str  # "text" или "voice"
    original_text: Optional[str] = None
    processed_text: Optional[str] = None
    voice_file_id: Optional[str] = None
    documents: List[str] = None  # Список file_id
    urgency: str = 'normal'  # "urgent", "normal", "complex"
    created_at: datetime = datetime.now()
    status: str = "pending"
