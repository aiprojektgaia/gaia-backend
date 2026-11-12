from typing import Any
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.dialects.postgresql import JSON


class Base(DeclarativeBase):
    id: Any
    __name__: str

    # to generate tablename from classname
    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__.lower()

    # mapping json supported by postgres
    type_annotation_map = {dict[str, Any]: JSON}
