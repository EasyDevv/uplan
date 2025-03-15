from typing import List, Dict
from pydantic import BaseModel, RootModel


class TodoItem(BaseModel):
    frameworks: List[str]
    tasks: List[str]


class TodoModel(RootModel[Dict[str, TodoItem]]):
    pass
