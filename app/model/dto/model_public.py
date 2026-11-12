from pydantic import BaseModel


class ModelPublic(BaseModel):
    id: int
    name: str
    description: str | None