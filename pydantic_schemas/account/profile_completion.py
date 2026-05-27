from pydantic import BaseModel


class ProfileCompletionItem(BaseModel):
    key: str
    title: str
    subtitle: str
    completed: bool
    weight: int = 1


class ProfileCompletionResponse(BaseModel):
    role: str
    score: int
    completed: int
    total: int
    title: str
    subtitle: str
    items: list[ProfileCompletionItem]
