from typing import Any
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    id: Any
    __name__: str

    # Automatically generate table name from class name
    @declared_attr
    def __tablename__(cls) -> str:
        # Convert CamelCase to snake_case
        import re
        name = cls.__name__
        # Add underscore between lower and upper case letters
        name = re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()
        # Pluralize simple names
        if name.endswith('y'):
            return name[:-1] + 'ies'
        elif name.endswith('s'):
            return name
        return name + 's'
