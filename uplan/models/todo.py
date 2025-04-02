from pydantic import BaseModel, RootModel
from typing import List, Dict


# Represents the structure under each key within the [template] table
# e.g., [template.environment_setup], [template.frontend]
class TemplateItem(BaseModel):
    frameworks: List[str]
    tasks: List[str]


# Represents ONLY the structure of the [template] section in todo.toml
# It expects a dictionary where keys are template names (str)
# and values are TemplateItem objects.
class TodoModel(RootModel[Dict[str, TemplateItem]]):
    pass
