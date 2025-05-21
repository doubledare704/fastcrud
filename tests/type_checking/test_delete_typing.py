"""
This file is intended for static type checking with mypy, not for pytest execution.
It helps verify the type hints for the delete and db_delete methods of FastCRUD,
especially with the introduction of the 'filters: DeleteSchemaType' parameter.
"""
from typing import Any, TypeVar, Generic
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import declarative_base
from pydantic import BaseModel
import datetime # For db_row, even if not directly used in delete filters

from fastcrud.crud.fast_crud import FastCRUD

# Define a SQLAlchemy model for type checking
Base: Any = declarative_base()

class TypeCheckModel(Base):
    __tablename__ = "type_check_items"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)

# Define Pydantic schemas for type checking
class TypeCheckBaseSchema(BaseModel):
    name: str

class TypeCheckCreateSchema(TypeCheckBaseSchema):
    pass

class TypeCheckUpdateSchema(TypeCheckBaseSchema):
    name: str | None = None # To match UpdateSchemaType definition

class TypeCheckDeleteSchema(BaseModel):
    id: int

# For FastCRUD generic type hints
ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)
DeleteSchemaType = TypeVar("DeleteSchemaType", bound=BaseModel)


# Initialize FastCRUD with type arguments
crud_typed = FastCRUD[
    TypeCheckModel,
    TypeCheckCreateSchema,
    TypeCheckUpdateSchema,
    TypeCheckUpdateSchema, # UpdateSchemaInternalType, can be same as UpdateSchemaType
    TypeCheckDeleteSchema,
]

# Dummy AsyncSession for type hinting
class DummyAsyncSession:
    async def commit(self) -> None:
        pass
    # Add other methods if mypy needs them based on FastCRUD usage
    # For delete, commit is the main one after execute (which is internal)

mock_db_session: AsyncSession = DummyAsyncSession() # type: ignore


# --- Test cases for `delete` method ---

async def typed_delete_with_filters_param(item_id: int) -> None:
    """mypy should correctly type-check this call."""
    delete_filter = TypeCheckDeleteSchema(id=item_id)
    await crud_typed.delete(db=mock_db_session, filters=delete_filter)

async def typed_delete_with_extra_filters_dict(item_id: int) -> None:
    """mypy should accept this, extra_filters is Any."""
    await crud_typed.delete(db=mock_db_session, extra_filters={"id": item_id})

async def typed_delete_with_kwargs_as_extra_filters(item_id: int) -> None:
    """
    mypy might have issues here if strict type checking for kwargs is enforced
    without explicit parameters matching 'id'.
    However, **extra_filters: Any should allow this.
    """
    await crud_typed.delete(db=mock_db_session, id=item_id) # type: ignore

async def typed_delete_with_filters_and_extra_filters(item_id: int, name_filter: str) -> None:
    """mypy should accept this."""
    delete_filter = TypeCheckDeleteSchema(id=item_id)
    await crud_typed.delete(db=mock_db_session, filters=delete_filter, extra_filters={"name": name_filter})

async def typed_delete_with_filters_and_kwargs(item_id: int, name_filter: str) -> None:
    """mypy should accept this, kwargs go to extra_filters."""
    delete_filter = TypeCheckDeleteSchema(id=item_id)
    await crud_typed.delete(db=mock_db_session, filters=delete_filter, name=name_filter) # type: ignore

async def typed_delete_no_filters_value_error_path() -> None:
    """
    This should raise a ValueError at runtime.
    Mypy doesn't check runtime logic, but the call signature is valid.
    """
    # await crud_typed.delete(db=mock_db_session) # This line would be a runtime error
    pass


# --- Test cases for `db_delete` method ---

async def typed_db_delete_with_filters_param(item_id: int) -> None:
    """mypy should correctly type-check this call."""
    delete_filter = TypeCheckDeleteSchema(id=item_id)
    await crud_typed.db_delete(db=mock_db_session, filters=delete_filter)

async def typed_db_delete_with_extra_filters_dict(item_id: int) -> None:
    """mypy should accept this, extra_filters is Any."""
    await crud_typed.db_delete(db=mock_db_session, extra_filters={"id": item_id})

async def typed_db_delete_with_kwargs_as_extra_filters(item_id: int) -> None:
    """
    Similar to delete, **extra_filters: Any should allow this.
    """
    await crud_typed.db_delete(db=mock_db_session, id=item_id) # type: ignore

async def typed_db_delete_with_filters_and_extra_filters(item_id: int, name_filter: str) -> None:
    """mypy should accept this."""
    delete_filter = TypeCheckDeleteSchema(id=item_id)
    await crud_typed.db_delete(db=mock_db_session, filters=delete_filter, extra_filters={"name": name_filter})

async def typed_db_delete_with_filters_and_kwargs(item_id: int, name_filter: str) -> None:
    """mypy should accept this, kwargs go to extra_filters."""
    delete_filter = TypeCheckDeleteSchema(id=item_id)
    await crud_typed.db_delete(db=mock_db_session, filters=delete_filter, name=name_filter) # type: ignore

async def typed_db_delete_no_filters_value_error_path() -> None:
    """
    This should raise a ValueError at runtime.
    Mypy doesn't check runtime logic, but the call signature is valid.
    """
    # await crud_typed.db_delete(db=mock_db_session) # This line would be a runtime error
    pass

# Example of how this file might be checked (not part of the file itself):
# mypy --strict tests/type_checking/test_delete_typing.py
#
# Note on `type: ignore`:
# The `id=item_id` and `name=name_filter` kwargs for delete/db_delete are passed to **extra_filters.
# While this is valid Python, mypy with strict settings might complain about unexpected keyword arguments
# if it cannot perfectly infer the target of **extra_filters or if the FastCRUD class itself
# isn't fully transparent to mypy for such dynamic kwargs without explicit parameters.
# The `filters` parameter is the type-safer way. The ignores are there to acknowledge this potential
# mypy strictness vs. runtime flexibility. If mypy is configured to be less strict about
# **kwargs, these ignores might not be necessary.
#
# The primary goal is to ensure `filters=DeleteSchemaType` is correctly typed.
# The `DeleteSchemaType` in `FastCRUD` is a TypeVar, so `crud_typed.delete(filters=...)`
# should correctly expect `TypeCheckDeleteSchema` or `None`.
#
# If `DeleteSchemaType` was not bound (e.g. `DeleteSchemaType = Any`), then `filters` would be `Any`.
# But since it's `DeleteSchemaType = TypeVar("DeleteSchemaType", bound=BaseModel)`,
# and we provided `TypeCheckDeleteSchema` in `FastCRUD[..., TypeCheckDeleteSchema]`,
# mypy should enforce that `filters` is `Optional[TypeCheckDeleteSchema]`.

```
