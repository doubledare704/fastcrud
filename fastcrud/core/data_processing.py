"""
Pure data transformation functions for processing joined data structures.

This module contains stateless functions for transforming flat joined data into
nested structures. All functions are pure (no side effects) and focus on
data manipulation without expensive operations.
"""

from typing import Any, Optional, Union, TYPE_CHECKING, Callable
from ..types import SelectSchemaType
from .introspection import get_primary_key_names

if TYPE_CHECKING:
    from .config import JoinConfig
    from sqlalchemy.ext.asyncio import AsyncSession


def handle_one_to_one(
    nested_data: dict[str, Any], nested_key: str, nested_field: str, value: Any
) -> dict[str, Any]:
    """
    Handles the nesting of one-to-one relationships in the data.

    Args:
        nested_data: The current state of the nested data.
        nested_key: The key under which the nested data should be stored.
        nested_field: The field name of the nested data to be added.
        value: The value of the nested data to be added.

    Returns:
        dict[str, Any]: The updated nested data dictionary.

    Examples:

        Input:

        ```python
        nested_data = {
            'id': 1,
            'name': 'Test Author',
        }
        nested_key = 'profile'
        nested_field = 'bio'
        value = 'This is a bio.'
        ```

        Output:

        ```json
        {
            'id': 1,
            'name': 'Test Author',
            'profile': {
                'bio': 'This is a bio.'
            }
        }
        ```
    """
    if nested_key not in nested_data or not isinstance(nested_data[nested_key], dict):
        nested_data[nested_key] = {}
    nested_data[nested_key][nested_field] = value
    return nested_data


def handle_one_to_many(
    nested_data: dict[str, Any], nested_key: str, nested_field: str, value: Any
) -> dict[str, Any]:
    """
    Handles the nesting of one-to-many relationships in the data.

    Args:
        nested_data: The current state of the nested data.
        nested_key: The key under which the nested data should be stored.
        nested_field: The field name of the nested data to be added.
        value: The value of the nested data to be added.

    Returns:
        dict[str, Any]: The updated nested data dictionary.

    Examples:

        Input:

        ```python
        nested_data = {
            'id': 1,
            'name': 'Test Author',
            'articles': [
                {
                    'title': 'First Article',
                    'content': 'Content of the first article!',
                }
            ],
        }
        nested_key = 'articles'
        nested_field = 'title'
        value = 'Second Article'
        ```

        Output:

        ```json
        {
            'id': 1,
            'name': 'Test Author',
            'articles': [
                {
                    'title': 'First Article',
                    'content': 'Content of the first article!'
                },
                {
                    'title': 'Second Article'
                }
            ]
        }
        ```

        Input:

        ```python
        nested_data = {
            'id': 1,
            'name': 'Test Author',
            'articles': [],
        }
        nested_key = 'articles'
        nested_field = 'title'
        value = 'First Article'
        ```

        Output:

        ```json
        {
            'id': 1,
            'name': 'Test Author',
            'articles': [
                {
                    'title': 'First Article'
                }
            ]
        }
        ```
    """
    if nested_key not in nested_data or not isinstance(nested_data[nested_key], list):
        nested_data[nested_key] = []

    if not nested_data[nested_key] or nested_field in nested_data[nested_key][-1]:
        nested_data[nested_key].append({nested_field: value})
    else:
        nested_data[nested_key][-1][nested_field] = value

    return nested_data


def sort_nested_list(
    nested_list: list[dict],
    sort_columns: Union[str, list[str]],
    sort_orders: Optional[Union[str, list[str]]] = None,
) -> list[dict]:
    """
    Sorts a list of dictionaries based on specified sort columns and orders.

    Args:
        nested_list: The list of dictionaries to sort.
        sort_columns: A single column name or a list of column names on which to apply sorting.
        sort_orders: A single sort order ("asc" or "desc") or a list of sort orders corresponding
            to the columns in `sort_columns`. If not provided, defaults to "asc" for each column.

    Returns:
        The sorted list of dictionaries.

    Examples:
        Sorting a list of dictionaries by a single column in ascending order:
        >>> sort_nested_list([{"id": 2, "name": "B"}, {"id": 1, "name": "A"}], "name")
        [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]

        Sorting by multiple columns with different orders:
        >>> sort_nested_list([{"id": 1, "name": "A"}, {"id": 2, "name": "A"}], ["name", "id"], ["asc", "desc"])
        [{"id": 2, "name": "A"}, {"id": 1, "name": "A"}]
    """
    if not nested_list or not sort_columns:
        return nested_list

    if not isinstance(sort_columns, list):
        sort_columns = [sort_columns]

    if sort_orders:
        if not isinstance(sort_orders, list):
            sort_orders = [sort_orders] * len(sort_columns)
        if len(sort_columns) != len(sort_orders):
            raise ValueError("The length of sort_columns and sort_orders must match.")

        for order in sort_orders:
            if order not in ["asc", "desc"]:
                raise ValueError(
                    f"Invalid sort order: {order}. Only 'asc' or 'desc' are allowed."
                )
    else:
        sort_orders = ["asc"] * len(sort_columns)

    sort_specs = [
        (col, 1 if order == "asc" else -1)
        for col, order in zip(sort_columns, sort_orders)
    ]

    sorted_list = nested_list.copy()
    for col, direction in reversed(sort_specs):
        sorted_list.sort(
            key=lambda x: (x.get(col) is None, x.get(col)), reverse=direction == -1
        )

    return sorted_list


def get_nested_key_for_join(join_config: "JoinConfig") -> str:
    """
    Determines the nested key name for a join configuration in the result data structure.

    This function extracts the appropriate key name that will be used to nest joined data
    in the final result. It prioritizes the custom join_prefix if provided, otherwise
    falls back to the model's table name.

    Args:
        join_config: The join configuration instance containing join configuration details.

    Returns:
        The string key name to be used for nesting the joined data.

    Examples:
        >>> class JoinConfig:
        ...     def __init__(self, model, join_prefix=None):
        ...         self.model = model
        ...         self.join_prefix = join_prefix
        ...
        >>> class Article:
        ...     __tablename__ = "articles"
        ...
        >>> join_config = JoinConfig(Article, join_prefix="articles_")
        >>> get_nested_key_for_join(join_config)
        "articles"

        >>> join_config = JoinConfig(Article)  # No prefix specified
        >>> get_nested_key_for_join(join_config)
        "articles"  # Uses model.__tablename__
    """
    return (
        join_config.join_prefix.rstrip("_")
        if join_config.join_prefix
        else join_config.model.__tablename__
    )


def process_joined_field(
    nested_data: dict[str, Any],
    join_config: "JoinConfig",
    nested_field: str,
    value: Any,
) -> dict[str, Any]:
    """
    Processes a single joined field and updates the nested data structure accordingly.

    This function handles the nesting of a single field from joined table data based on the
    relationship type defined in the join configuration. It delegates to the appropriate
    handler function for one-to-one or one-to-many relationships.

    Args:
        nested_data: The current nested data dictionary being built.
        join_config: The join configuration instance defining the join relationship type and configuration.
        nested_field: The name of the field being processed from the joined table.
        value: The value of the field being processed.

    Returns:
        The updated nested data dictionary with the processed field added.

    Examples:
        >>> nested_data = {"id": 1, "title": "Test"}
        >>> class MockJoinConfig:
        ...     relationship_type = "one-to-many"
        ...     join_prefix = "articles_"
        ...     model = type("Article", (), {"__tablename__": "articles"})
        >>> join_config = MockJoinConfig()
        >>> result = process_joined_field(nested_data, join_config, "title", "Article 1")
        >>> # Returns updated nested_data with article data nested appropriately
    """
    nested_key = get_nested_key_for_join(join_config)

    if join_config.relationship_type == "one-to-many":
        return handle_one_to_many(nested_data, nested_key, nested_field, value)
    else:
        return handle_one_to_one(nested_data, nested_key, nested_field, value)


def process_data_fields(
    data: dict,
    join_definitions: list["JoinConfig"],
    temp_prefix: str,
    nested_data: dict[str, Any],
) -> dict[str, Any]:
    """
    Processes all fields in the flat data dictionary and nests joined data according to join definitions.

    This function iterates through all key-value pairs in the input data, identifying which fields
    belong to joined tables based on their prefixes, and nests them under their appropriate parent
    keys. Fields that don't match any join prefix are added directly to the nested data.

    Args:
        data: The flat dictionary containing data with potentially prefixed keys from joined tables.
        join_definitions: List of join configuration instances defining how to identify and nest joined data.
        temp_prefix: The temporary prefix used to identify joined fields (e.g., "joined__").
        nested_data: The target dictionary where nested data will be organized.

    Returns:
        The updated nested data dictionary with all fields properly organized.

    Example:
        Input data: {
            "id": 1,
            "name": "Author 1",
            "joined__articles_id": 10,
            "joined__articles_title": "Article Title"
        }

        Output: {
            "id": 1,
            "name": "Author 1",
            "articles": [{"id": 10, "title": "Article Title"}]
        }
    """
    for key, value in data.items():
        nested = False
        for join in join_definitions:
            join_prefix = join.join_prefix or ""
            full_prefix = f"{temp_prefix}{join_prefix}"

            if isinstance(key, str) and key.startswith(full_prefix):
                nested_field = key[len(full_prefix) :]
                nested_data = process_joined_field(
                    nested_data, join, nested_field, value
                )
                nested = True
                break

        if not nested:
            stripped_key = (
                key[len(temp_prefix) :]
                if isinstance(key, str) and key.startswith(temp_prefix)
                else key
            )
            nested_data[stripped_key] = value

    return nested_data


def cleanup_null_joins(
    nested_data: dict[str, Any],
    join_definitions: list["JoinConfig"],
    get_primary_key_func: Callable,
) -> dict[str, Any]:
    """
    Cleans up nested join data by handling null primary keys and applying sorting configurations.

    This function performs post-processing on nested join data to:
    1. Remove or replace entries with null primary keys (indicating no actual joined data)
    2. Apply sorting to one-to-many relationships when sort configurations are specified
    3. Convert one-to-one relationships with null primary keys to None

    Args:
        nested_data: The nested data dictionary containing organized joined data.
        join_definitions: List of join configuration instances with sorting and relationship configurations.
        get_primary_key_func: Function to get the primary key for a model.

    Returns:
        The cleaned nested data dictionary with null entries handled and sorting applied.

    Example:
        Before cleanup:
        {
            "id": 1,
            "articles": [{"id": None, "title": None}, {"id": 2, "title": "Real Article"}],
            "profile": {"id": None, "bio": None}
        }

        After cleanup:
        {
            "id": 1,
            "articles": [{"id": 2, "title": "Real Article"}],  # Null entry removed
            "profile": None  # Null one-to-one converted to None
        }
    """
    for join in join_definitions:
        join_primary_key = get_primary_key_func(join.model)
        nested_key = get_nested_key_for_join(join)

        if join.relationship_type == "one-to-many" and nested_key in nested_data:
            if isinstance(nested_data.get(nested_key, []), list):
                if any(
                    item[join_primary_key] is None for item in nested_data[nested_key]
                ):
                    nested_data[nested_key] = []
                elif join.sort_columns and nested_data[nested_key]:
                    nested_data[nested_key] = sort_nested_list(
                        nested_data[nested_key], join.sort_columns, join.sort_orders
                    )

        if nested_key in nested_data and isinstance(nested_data[nested_key], dict):
            if (
                join_primary_key in nested_data[nested_key]
                and nested_data[nested_key][join_primary_key] is None
            ):
                nested_data[nested_key] = None

    return nested_data


def nest_join_data(
    data: dict,
    join_definitions: list["JoinConfig"],
    get_primary_key_func: Callable,
    temp_prefix: str = "joined__",
    nested_data: Optional[dict[str, Any]] = None,
) -> dict:
    """
    Nests joined data based on join definitions provided. This function processes the input `data` dictionary,
    identifying keys that correspond to joined tables using the provided `join_definitions` and nest them
    under their respective table keys.

    Args:
        data: The flat dictionary containing data with potentially prefixed keys from joined tables.
        join_definitions: A list of join configuration instances defining the join configurations, including prefixes.
        get_primary_key_func: Function to get the primary key for a model.
        temp_prefix: The temporary prefix applied to joined columns to differentiate them. Defaults to `"joined__"`.
        nested_data: The nested dictionary to which the data will be added. If None, a new dictionary is created. Defaults to `None`.

    Returns:
        dict[str, Any]: A dictionary with nested structures for joined table data.

    Examples:

        Input:

        ```python
        data = {
            'id': 1,
            'title': 'Test Author',
            'joined__articles_id': 1,
            'joined__articles_title': 'Article 1',
            'joined__articles_author_id': 1
        }

        join_definitions = [
            JoinConfig(
                model=Article,
                join_prefix='articles_',
                relationship_type='one-to-many',
            ),
        ]
        ```

        Output:

        ```json
        {
            'id': 1,
            'title': 'Test Author',
            'articles': [
                {
                    'id': 1,
                    'title': 'Article 1',
                    'author_id': 1
                }
            ]
        }
        ```

        Input:

        ```python
        data = {
            'id': 1,
            'title': 'Test Article',
            'joined__author_id': 1,
            'joined__author_name': 'Author 1'
        }

        join_definitions = [
            JoinConfig(
                model=Author,
                join_prefix='author_',
                relationship_type='one-to-one',
            ),
        ]
        ```

        Output:

        ```json
        {
            'id': 1,
            'title': 'Test Article',
            'author': {
                'id': 1,
                'name': 'Author 1'
            }
        }
        ```
    """
    if nested_data is None:
        nested_data = {}

    nested_data = process_data_fields(data, join_definitions, temp_prefix, nested_data)
    nested_data = cleanup_null_joins(
        nested_data, join_definitions, get_primary_key_func
    )

    assert nested_data is not None, "Couldn't nest the data."
    return nested_data


def build_column_label(temp_prefix: str, prefix: Optional[str], field_name: str) -> str:
    """
    Builds a column label with appropriate prefixes for SQLAlchemy column selection.

    Args:
        temp_prefix: The temporary prefix to be prepended to the column label.
        prefix: Optional prefix to be added between temp_prefix and field_name. If None, only temp_prefix is used.
        field_name: The base field name for the column.

    Returns:
        A formatted column label string combining the prefixes and field name.

    Examples:
        >>> build_column_label("joined__", "articles_", "title")
        "joined__articles_title"

        >>> build_column_label("joined__", None, "id")
        "joined__id"
    """
    if prefix:
        return f"{temp_prefix}{prefix}{field_name}"
    else:
        return f"{temp_prefix}{field_name}"


def convert_to_pydantic_models(
    nested_data: list,
    schema_to_select: type[SelectSchemaType],
    nested_schema_to_select: Optional[dict[str, type[SelectSchemaType]]],
) -> list:
    """
    Converts nested dictionary data to Pydantic model instances.

    This function takes the nested dictionary data structure created by the join processing
    and converts it to properly typed Pydantic models. It handles both the main records
    and any nested joined data, applying the appropriate schemas to each level.

    Args:
        nested_data: List of dictionaries containing the nested data to be converted.
        schema_to_select: The main Pydantic schema class for the base records.
        nested_schema_to_select: Optional mapping of join prefixes to their corresponding schemas.

    Returns:
        List of Pydantic model instances with properly nested related data.

    Example:
        >>> nested_data = [
        ...     {
        ...         "id": 1,
        ...         "name": "Author 1",
        ...         "articles": [{"id": 10, "title": "Article 1"}]
        ...     }
        ... ]
        >>> schemas = {"articles_": ArticleSchema}
        >>> result = convert_to_pydantic_models(nested_data, AuthorSchema, schemas)
        >>> # Returns [AuthorSchema(id=1, name="Author 1", articles=[ArticleSchema(...)])]
    """
    converted_data = []
    for item in nested_data:
        if nested_schema_to_select:
            for prefix, nested_schema in nested_schema_to_select.items():
                prefix_key = prefix.rstrip("_")
                if prefix_key in item:
                    if isinstance(item[prefix_key], list):
                        item[prefix_key] = [
                            nested_schema(**nested_item)
                            for nested_item in item[prefix_key]
                        ]
                    else:
                        item[prefix_key] = (
                            nested_schema(**item[prefix_key])
                            if item[prefix_key] is not None
                            else None
                        )

        converted_data.append(schema_to_select(**item))
    return converted_data


def format_single_response(
    data: Any, schema_to_select: Optional[type] = None, return_as_model: bool = False
) -> Union[dict, Any]:
    """
    Format single record response with optional model conversion.

    Port of FastCRUD._as_single_response logic.

    Args:
        data: Raw data from database query result
        schema_to_select: Pydantic schema for model conversion
        return_as_model: Whether to convert to Pydantic model

    Returns:
        Formatted single record (dict or Pydantic model)

    Raises:
        ValueError: If schema_to_select required but not provided
    """
    if not return_as_model:
        return data

    if not schema_to_select:
        raise ValueError(
            "schema_to_select must be provided when return_as_model is True."
        )

    return schema_to_select(**data)


def format_multi_response(
    data: list[Any],
    schema_to_select: Optional[type] = None,
    return_as_model: bool = False,
) -> list[Any]:
    """
    Format multiple records response with optional model conversion.

    Port of FastCRUD._as_multi_response logic.

    Args:
        data: List of raw data from database query results
        schema_to_select: Pydantic schema for model conversion
        return_as_model: Whether to convert to Pydantic models

    Returns:
        List of formatted records (dicts or Pydantic models)

    Raises:
        ValueError: If schema_to_select required but not provided
        ValidationError: If data validation fails during model conversion
    """
    if not return_as_model:
        return data

    if not schema_to_select:
        raise ValueError(
            "schema_to_select must be provided when return_as_model is True"
        )

    try:
        converted_data = []
        for row in data:
            if isinstance(row, dict):
                converted_data.append(schema_to_select(**row))
            else:
                converted_data.append(row)
        return converted_data
    except Exception as e:
        raise ValueError(
            f"Data validation error for schema {schema_to_select.__name__}: {e}"
        )


def create_paginated_response_data(
    items: list,
    total_count: int,
    offset: int = 0,
    limit: Optional[int] = None,
    data_key: str = "data",
) -> dict[str, Any]:
    """
    Create paginated response data structure.

    Combines items with pagination metadata in a standardized format.

    Args:
        items: List of data items to include in response
        total_count: Total number of items available (for pagination)
        offset: Number of items skipped (default: 0)
        limit: Maximum number of items per page (default: None - no limit)
        data_key: Key name for the data items (default: "data")

    Returns:
        Dictionary containing items and pagination metadata

    Example:
        >>> create_paginated_response_data([item1, item2], 50, 20, 10)
        {
            "data": [item1, item2],
            "total_count": 50,
            "has_more": True,
            "offset": 20,
            "limit": 10
        }

    """
    response = {
        data_key: items,
        "total_count": total_count,
    }

    if limit is not None:
        response["has_more"] = (offset + len(items)) < total_count
        response["offset"] = offset
        response["limit"] = limit

    return response


def process_joined_data(
    data_list: list[dict],
    join_definitions: list["JoinConfig"],
    nest_joins: bool,
    primary_model: Any,
) -> Optional[dict[str, Any]]:
    """
    Process joined data using core utilities for nesting and relationships.

    Args:
        data_list: List of flat dictionaries containing joined data
        join_definitions: List of join configurations
        nest_joins: Whether to nest the joined data
        primary_model: Primary SQLAlchemy model class

    Returns:
        Processed nested data dictionary or None if no data
    """
    if not data_list:
        return None

    if not nest_joins:
        return data_list[0]

    one_to_many_count = sum(
        1 for join in join_definitions if join.relationship_type == "one-to-many"
    )

    if one_to_many_count > 1:
        pre_nested_data = []
        for row_data in data_list:
            nested_row = nest_join_data(
                data=row_data,
                join_definitions=join_definitions,
                get_primary_key_func=lambda model: get_primary_key_names(model)[0],
            )
            pre_nested_data.append(nested_row)

        from .join_processing import JoinProcessor

        processor = JoinProcessor(primary_model)
        nested_results = processor.process_multi_join(
            data=pre_nested_data,
            joins_config=join_definitions,
            return_as_model=False,
            schema_to_select=None,
            nested_schema_to_select={
                (
                    join.join_prefix.rstrip("_")
                    if join.join_prefix
                    else join.model.__tablename__
                ): join.schema_to_select
                for join in join_definitions
                if join.schema_to_select
            },
        )
        return dict(nested_results[0]) if nested_results else {}
    else:
        nested_data: dict = {}
        for data in data_list:
            nested_data = nest_join_data(
                data,
                join_definitions,
                lambda model: get_primary_key_names(model)[0],
                nested_data=nested_data,
            )
        return nested_data


async def format_joined_response(
    primary_model: Any,
    raw_data: list[dict],
    config: dict[str, Any],
    schema_to_select: Optional[type[SelectSchemaType]] = None,
    return_as_model: bool = False,
    nest_joins: bool = False,
    return_total_count: bool = True,
    db: Optional["AsyncSession"] = None,
    nested_schema_to_select: Optional[dict[str, type[SelectSchemaType]]] = None,
    count_func: Optional[Callable] = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Format response using core utilities.

    Args:
        primary_model: Primary SQLAlchemy model class
        raw_data: Raw query results
        config: Configuration dictionary with join_definitions
        schema_to_select: Pydantic schema for response formatting
        return_as_model: Whether to return as Pydantic model
        nest_joins: Whether joins are nested
        return_total_count: Whether to include total count
        db: Database session (for count queries)
        nested_schema_to_select: Schemas for nested data
        count_func: Function to get total count
        **kwargs: Additional filter parameters

    Returns:
        Formatted response dictionary
    """
    from typing import cast

    join_definitions = config["join_definitions"]

    processed_data = []
    for row_dict in raw_data:
        if nest_joins:
            row_dict = nest_join_data(
                data=row_dict,
                join_definitions=join_definitions,
                get_primary_key_func=lambda model: get_primary_key_names(model)[0],
            )
        processed_data.append(row_dict)

    nested_data: list[Union[dict[str, Any], SelectSchemaType]]
    if nest_joins and any(
        join.relationship_type == "one-to-many" for join in join_definitions
    ):
        from .join_processing import JoinProcessor

        processor = JoinProcessor(primary_model)
        nested_result = processor.process_multi_join(
            data=processed_data,
            joins_config=join_definitions,
            return_as_model=return_as_model,
            schema_to_select=schema_to_select if return_as_model else None,
            nested_schema_to_select=nested_schema_to_select
            or {
                (
                    join.join_prefix.rstrip("_")
                    if join.join_prefix
                    else join.model.__tablename__
                ): join.schema_to_select
                for join in join_definitions
                if join.schema_to_select
            },
        )
        nested_data = list(nested_result)
    else:
        from .join_processing import handle_null_primary_key_multi_join

        nested_data = handle_null_primary_key_multi_join(
            cast(list[Union[dict[str, Any], SelectSchemaType]], processed_data),
            join_definitions,
        )

    formatted_data: list[Any] = format_multi_response(
        nested_data, schema_to_select, return_as_model
    )
    response: dict[str, Any] = {"data": formatted_data}

    if return_total_count and db and count_func:
        distinct_on_primary = bool(
            nest_joins
            and any(j.relationship_type == "one-to-many" for j in join_definitions)
        )
        non_filter_params = {
            "schema_to_select",
            "join_model",
            "join_on",
            "join_prefix",
            "join_schema_to_select",
            "join_type",
            "alias",
            "join_filters",
            "nest_joins",
            "offset",
            "limit",
            "sort_columns",
            "sort_orders",
            "return_as_model",
            "joins_config",
            "counts_config",
            "return_total_count",
            "relationship_type",
            "nested_schema_to_select",
        }
        filter_kwargs = {k: v for k, v in kwargs.items() if k not in non_filter_params}
        total_count: int = await count_func(
            db=db,
            joins_config=join_definitions,
            distinct_on_primary=distinct_on_primary,
            **filter_kwargs,
        )
        response["total_count"] = total_count

    return response
