from pydantic import BaseModel
from typing import Optional, List

class FilterParams(BaseModel):
    date_gte: Optional[str] = None
    date_lte: Optional[str] = None
    source_type: Optional[str] = None
    entity_names: Optional[List[str]] = None
