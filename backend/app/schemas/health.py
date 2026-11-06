from typing import Dict

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    app: str
    env: str
    checks: Dict[str, str]
