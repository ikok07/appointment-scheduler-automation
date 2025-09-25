from typing import Literal

from pydantic import BaseModel


class GenericResponse(BaseModel):
    status: Literal["success"] = "success"
    data: dict | list[dict] | None = None