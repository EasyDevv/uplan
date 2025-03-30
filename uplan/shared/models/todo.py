from typing import List, Dict
from pydantic import BaseModel, RootModel


class Category(BaseModel):
    title: str
    tasks: List[str]


class TodoItem(BaseModel):
    frameworks: List[str]
    categories: List[Category]


class TodoModel(RootModel[Dict[str, TodoItem]]):
    pass
