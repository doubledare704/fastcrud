"""
Schema and field injection utilities with caching for performance optimization.

This module provides functions for managing Pydantic schemas, field injection,
and column extraction with caching where beneficial for performance.
"""

import inspect
from functools import lru_cache
from typing import Callable, Any, Optional, Union, Sequence
from pydantic import BaseModel
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm.util import AliasedClass
from fastapi import Depends, Query, params

from .introspection import validate_model_has_table
from .data_processing import build_column_label
from ..types import ModelType, SelectSchemaType

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import CreateConfig, UpdateConfig, DeleteConfig, FilterConfig


@lru_cache(maxsize=128)
def create_modified_schema(
    original_schema: type[BaseModel],
    exclude_fields: tuple[str, ...],
    schema_name: str = "ModifiedSchema",
) -> type[BaseModel]:
    """
    Creates a new Pydantic schema with specified fields excluded - expensive operation, cache it.

    This function dynamically creates a new Pydantic schema class that excludes certain fields
    from the original schema. This is particularly useful for auto field injection where
    certain fields should not appear in API documentation or request schemas.

    Args:
        original_schema: The original Pydantic schema class.
        exclude_fields: Tuple of field names to exclude (tuple for cache hashability).
        schema_name: Name for the new schema class.

    Returns:
        A new Pydantic schema class without the excluded fields.

    Example:
        >>> class UserSchema(BaseModel):
        ...     id: int
        ...     name: str
        ...     email: str
        ...     password: str
        ...
        >>> # Create schema without sensitive fields
        >>> public_schema = create_modified_schema(
        ...     UserSchema,
        ...     ("password",),
        ...     "PublicUserSchema"
        ... )
        >>> # New schema only has id, name, email fields
    """
    if not exclude_fields:
        return original_schema

    from pydantic import create_model

    field_definitions: dict[str, Any] = {}
    for field_name, field_info in original_schema.model_fields.items():
        if field_name not in exclude_fields:
            field_definitions[field_name] = (field_info.annotation, field_info)

    new_schema: type[BaseModel] = create_model(
        schema_name,
        **field_definitions,  # type: ignore[arg-type]
    )

    return new_schema


def create_auto_field_injector(
    config: Optional[Union["CreateConfig", "UpdateConfig", "DeleteConfig"]],
) -> Callable[..., dict[str, Any]]:
    """
    Creates a dynamic dependency function that resolves auto_fields.

    Similar to create_dynamic_filters but for CreateConfig/UpdateConfig/DeleteConfig.
    Returns a function that can be used with Depends() to inject auto field values.

    Args:
        config: Configuration object containing auto_fields mapping.

    Returns:
        A dependency function that resolves auto field values.

    Example:
        >>> from datetime import datetime
        >>> from fastapi import Depends
        >>>
        >>> def get_current_user_id():
        ...     return 123
        >>>
        >>> def get_timestamp():
        ...     return datetime.now()
        >>>
        >>> config = CreateConfig(auto_fields={
        ...     "user_id": get_current_user_id,
        ...     "created_at": get_timestamp
        ... })
        >>>
        >>> injector = create_auto_field_injector(config)
        >>> # injector can now be used with FastAPI's Depends()
    """
    if config is None or not config.auto_fields:
        return lambda: {}

    def auto_fields_resolver(**kwargs: Any) -> dict[str, Any]:
        """Receives resolved dependency values and returns dict of field:value."""
        return kwargs

    params = []
    for field_name, func in config.auto_fields.items():
        params.append(
            inspect.Parameter(
                field_name,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                default=Depends(func),
            )
        )

    sig = inspect.Signature(params)
    setattr(auto_fields_resolver, "__signature__", sig)

    return auto_fields_resolver


def create_dynamic_filters(
    filter_config: Optional["FilterConfig"], column_types: dict[str, type]
) -> Callable[..., dict[str, Any]]:
    """
    Create dynamic filter function for handling query parameters.

    This function creates a dependency function that can parse and validate
    query parameters based on the filter configuration and column types.

    Args:
        filter_config: Configuration object defining available filters.
        column_types: Dictionary mapping column names to their Python types.

    Returns:
        A dependency function that processes filter parameters.

    Example:
        >>> filter_config = FilterConfig(filters={"name": None, "age__gte": 18})
        >>> column_types = {"name": str, "age": int}
        >>> filter_func = create_dynamic_filters(filter_config, column_types)
        >>> # filter_func can be used with FastAPI's Depends()
    """
    if filter_config is None:
        return lambda: {}

    param_to_filter_key = {}
    for original_key in filter_config.filters.keys():
        param_name = original_key.replace(".", "_")
        param_to_filter_key[param_name] = original_key

    def filters(
        **kwargs: Any,
    ) -> dict[str, Any]:
        filtered_params = {}
        for param_name, value in kwargs.items():
            if value is not None:
                original_key = param_to_filter_key.get(param_name, param_name)
                key_without_op = original_key.rsplit("__", 1)[0]
                parse_func = column_types.get(key_without_op)
                if parse_func:
                    try:
                        filtered_params[original_key] = parse_func(value)
                    except (ValueError, TypeError):
                        filtered_params[original_key] = value
                else:
                    filtered_params[original_key] = value
        return filtered_params

    params = []
    for key, value in filter_config.filters.items():
        param_name = key.replace(".", "_")

        if callable(value):
            params.append(
                inspect.Parameter(
                    param_name,
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    default=Depends(value),
                )
            )
        else:
            params.append(
                inspect.Parameter(
                    param_name,
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    default=Query(value, alias=key),
                )
            )

    sig = inspect.Signature(params)
    setattr(filters, "__signature__", sig)

    return filters


def extract_schema_columns(
    model_or_alias: Union[ModelType, AliasedClass],
    schema: type[SelectSchemaType],
    mapper,
    prefix: Optional[str],
    use_temporary_prefix: bool,
    temp_prefix: str,
) -> list[Any]:
    """
    Extracts specific columns from a SQLAlchemy model based on Pydantic schema field names.

    This function matches the field names defined in the provided Pydantic schema with the columns
    available in the SQLAlchemy model, excluding relationship fields. Each matched column can be
    optionally labeled with prefixes for use in joined queries.

    Args:
        model_or_alias: The SQLAlchemy model or its alias from which to extract columns.
        schema: The Pydantic schema containing field names to match against model columns.
        mapper: The SQLAlchemy mapper for the model, used to identify relationships.
        prefix: Optional prefix to be added to column labels. If None, no prefix is added.
        use_temporary_prefix: Whether to use the temporary prefix for column labeling.
        temp_prefix: The temporary prefix string to be used if use_temporary_prefix is True.

    Returns:
        A list of SQLAlchemy column objects, potentially with custom labels applied.

    Example:
        >>> schema = AuthorSchema  # Has fields: id, name, email
        >>> columns = extract_schema_columns(Author, schema, mapper, "author_", True, "joined__")
        >>> # Returns [Author.id.label("joined__author_id"), Author.name.label("joined__author_name"), ...]
    """
    columns = []
    for field in schema.model_fields.keys():
        if hasattr(model_or_alias, field) and field not in mapper.relationships:
            column = getattr(model_or_alias, field)
            if prefix is not None or use_temporary_prefix:
                column_label = build_column_label(temp_prefix, prefix, field)
                column = column.label(column_label)
            columns.append(column)
    return columns


def extract_all_columns(
    model_or_alias: Union[ModelType, AliasedClass],
    mapper,
    prefix: Optional[str],
    use_temporary_prefix: bool,
    temp_prefix: str,
) -> list[Any]:
    """
    Extracts all available columns from a SQLAlchemy model.

    This function retrieves all column attributes from the provided SQLAlchemy model,
    excluding relationship fields. Each column can be optionally labeled with prefixes
    for use in joined queries.

    Args:
        model_or_alias: The SQLAlchemy model or its alias from which to extract all columns.
        mapper: The SQLAlchemy mapper for the model, used to access column attributes.
        prefix: Optional prefix to be added to column labels. If None, no prefix is added.
        use_temporary_prefix: Whether to use the temporary prefix for column labeling.
        temp_prefix: The temporary prefix string to be used if use_temporary_prefix is True.

    Returns:
        A list of all SQLAlchemy column objects from the model, potentially with custom labels applied.

    Example:
        >>> columns = extract_all_columns(User, mapper, "user_", True, "joined__")
        >>> # Returns [User.id.label("joined__user_id"), User.name.label("joined__user_name"), ...]
    """
    columns = []
    for prop in mapper.column_attrs:
        column = getattr(model_or_alias, prop.key)
        if prefix is not None or use_temporary_prefix:
            column_label = build_column_label(temp_prefix, prefix, prop.key)
            column = column.label(column_label)
        columns.append(column)
    return columns


def extract_matching_columns_from_schema(
    model: Union[ModelType, AliasedClass],
    schema: Optional[type[SelectSchemaType]],
    prefix: Optional[str] = None,
    alias: Optional[AliasedClass] = None,
    use_temporary_prefix: Optional[bool] = False,
    temp_prefix: Optional[str] = "joined__",
) -> list[Any]:
    """
    Retrieves a list of ORM column objects from a SQLAlchemy model that match the field names in a given Pydantic schema,
    or all columns from the model if no schema is provided. When an alias is provided, columns are referenced through
    this alias, and a prefix can be applied to column names if specified.

    Args:
        model: The SQLAlchemy ORM model containing columns to be matched with the schema fields.
        schema: Optional; a Pydantic schema containing field names to be matched with the model's columns. If `None`, all columns from the model are used.
        prefix: Optional; a prefix to be added to all column names. If `None`, no prefix is added.
        alias: Optional; an alias for the model, used for referencing the columns through this alias in the query. If `None`, the original model is used.
        use_temporary_prefix: Whether to use or not an aditional prefix for joins. Default `False`.
        temp_prefix: The temporary prefix to be used. Default `"joined__"`.

    Returns:
        A list of ORM column objects (potentially labeled with a prefix) that correspond to the field names defined
        in the schema or all columns from the model if no schema is specified. These columns are correctly referenced
        through the provided alias if one is given.
    """
    validate_model_has_table(model)

    model_or_alias = alias if alias else model
    temp_prefix = (
        temp_prefix if use_temporary_prefix and temp_prefix is not None else ""
    )
    mapper = sa_inspect(model).mapper

    use_temp_prefix = (
        use_temporary_prefix if use_temporary_prefix is not None else False
    )
    if schema:
        return extract_schema_columns(
            model_or_alias, schema, mapper, prefix, use_temp_prefix, temp_prefix
        )
    else:
        return extract_all_columns(
            model_or_alias, mapper, prefix, use_temp_prefix, temp_prefix
        )


def inject_dependencies(
    funcs: Optional[Sequence[Callable]] = None,
) -> Optional[Sequence[params.Depends]]:
    """
    Wraps a list of functions in FastAPI's Depends.

    Args:
        funcs: Optional sequence of callable functions to wrap.

    Returns:
        Sequence of FastAPI Depends objects, or None if no functions provided.

    Raises:
        TypeError: If any function in the sequence is not callable.

    Example:
        >>> def get_current_user():
        ...     return {"id": 1}
        >>>
        >>> def get_permissions():
        ...     return ["read", "write"]
        >>>
        >>> deps = inject_dependencies([get_current_user, get_permissions])
        >>> # Returns [Depends(get_current_user), Depends(get_permissions)]
    """
    if funcs is None:
        return None

    for func in funcs:
        if not callable(func):
            raise TypeError(
                f"All dependencies must be callable. Got {type(func)} instead."
            )

    return [Depends(func) for func in funcs]


def apply_model_pk(**pkeys: type):
    """
    This decorator injects positional arguments into a fastCRUD endpoint.
    It dynamically changes the endpoint signature and allows to use
    multiple primary keys without defining them explicitly.

    Args:
        **pkeys: Dictionary mapping primary key names to their types.

    Returns:
        Decorator function that modifies endpoint signatures.

    Example:
        >>> from uuid import UUID
        >>>
        >>> @apply_model_pk(user_id=int, session_id=UUID)
        >>> def get_user_session(user_id: int, session_id: UUID, db: Session):
        ...     # Primary keys are automatically injected as path parameters
        ...     pass
    """
    from uuid import UUID
    from typing import Annotated
    from fastapi import Path

    def wrapper(endpoint):
        signature = inspect.signature(endpoint)
        parameters = [
            p
            for p in signature.parameters.values()
            if p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
        ]
        extra_positional_params = []
        for k, v in pkeys.items():
            if v == UUID:
                extra_positional_params.append(
                    inspect.Parameter(
                        name=k,
                        annotation=Annotated[UUID, Path(...)],
                        kind=inspect.Parameter.POSITIONAL_ONLY,
                    )
                )
            else:
                extra_positional_params.append(
                    inspect.Parameter(
                        name=k, annotation=v, kind=inspect.Parameter.POSITIONAL_ONLY
                    )
                )

        endpoint.__signature__ = signature.replace(
            parameters=extra_positional_params + parameters
        )
        return endpoint

    return wrapper


def auto_detect_join_condition(
    base_model: ModelType,
    join_model: ModelType,
):
    """
    Automatically detects the join condition for SQLAlchemy models based on foreign key relationships.

    Args:
        base_model: The base SQLAlchemy model from which to join.
        join_model: The SQLAlchemy model to join with the base model.

    Returns:
        A SQLAlchemy `ColumnElement` representing the join condition, if successfully detected.

    Raises:
        ValueError: If the join condition cannot be automatically determined.
        AttributeError: If either base_model or join_model does not have a `__table__` attribute.
    """
    from typing import cast
    from sqlalchemy.sql import ColumnElement

    validate_model_has_table(base_model)
    validate_model_has_table(join_model)

    inspector = sa_inspect(base_model)
    if inspector is not None:
        fk_columns = [col for col in inspector.c if col.foreign_keys]
        join_on = next(
            (
                cast(
                    ColumnElement,
                    base_model.__table__.c[col.name]
                    == join_model.__table__.c[list(col.foreign_keys)[0].column.name],
                )
                for col in fk_columns
                if list(col.foreign_keys)[0].column.table == join_model.__table__
            ),
            None,
        )

        if join_on is None:
            raise ValueError(
                "Could not automatically determine join condition. Please provide join_on."
            )
    else:
        raise ValueError("Could not automatically get model columns.")

    return join_on
