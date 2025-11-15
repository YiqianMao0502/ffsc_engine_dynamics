from dataclasses import dataclass
from typing import Optional, Dict, Any
@dataclass
class PlaceholderModel:
    chapter: str
    section: str
    name: str
    notes: str = "TODO: 等论文原文再补全实现。"
    extra: Optional[Dict[str, Any]] = None
