from typing import Any, Optional, Union, Sequence, cast

from sqlalchemy import inspect
from sqlalchemy.orm.util import AliasedClass
from sqlalchemy.sql import ColumnElement
from pydantic import BaseModel, ConfigDict
from pydantic.functional_validators import field_validator

from fastcrud.types import ModelType, SelectSchemaType

from ..endpoint.helper import (
    _get_primary_key,
    _get_primary_key_names,
    _create_composite_key,
)


class JoinConfig(BaseModel):
    model: Any
    join_on: Any
    join_prefix: Optional[str] = None
    schema_to_select: Optional[type[BaseModel]] = None
    join_type: str = "left"
    alias: Optional[AliasedClass] = None
    filters: Optional[dict] = None
    relationship_type: Optional[str] = "one-to-one"
    sort_columns: Optional[Union[str, list[str]]] = None
    sort_orders: Optional[Union[str, list[str]]] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("relationship_type")
    def check_valid_relationship_type(cls, value):
        valid_relationship_types = {"one-to-one", "one-to-many"}
        if value is not None and value not in valid_relationship_types:
            raise ValueError(f"Invalid relationship type: {value}")  # pragma: no cover
        return value

    @field_validator("join_type")
    def check_valid_join_type(cls, value):
        valid_join_types = {"left", "inner"}
        if value not in valid_join_types:
            raise ValueError(f"Unsupported join type: {value}")
        return value


class CountConfig(BaseModel):
    """
    Configuration for counting related objects in joined queries.

    This allows you to annotate query results with counts of related objects,
    particularly useful for many-to-many relationships. The count is implemented
    as a scalar subquery, which means all records from the primary model will be
    returned with their respective counts (including 0 for records with no related objects).

    Attributes:
        model: The SQLAlchemy model to count.
        join_on: The join condition for the count query.
        alias: Optional alias for the count column in the result. Defaults to "{model.__tablename__}_count".
        filters: Optional filters to apply to the count query.

    Example:
        ```python
        from fastcrud import FastCRUD, CountConfig

        # Count videos for each search through a many-to-many relationship
        count_config = CountConfig(
            model=Video,
            join_on=(Video.id == VideoSearchAssociation.video_id)
                   & (VideoSearchAssociation.search_id == Search.id),
            alias='videos_count'
        )

        search_crud = FastCRUD(Search)
        results = await search_crud.get_multi_joined(
            db=session,
            counts_config=[count_config],
        )
        # Results will include 'videos_count' field for each search
        # Example: [{"id": 1, "term": "cats", "videos_count": 5}, ...]
        ```
    """

    model: Any
    join_on: Any
    alias: Optional[str] = None
    filters: Optional[dict] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


def _validate_model_has_table(model: Union[ModelType, AliasedClass]) -> None:
    """Validates that a model has a __table__ attribute."""
    if not hasattr(model, "__table__"):  # pragma: no cover
        raise AttributeError(f"{model.__name__} does not have a '__table__' attribute.")


def _build_column_label(
    temp_prefix: str, prefix: Optional[str], field_name: str
) -> str:
    """
    Builds a column label with appropriate prefixes for SQLAlchemy column selection.

    Args:
        temp_prefix: The temporary prefix to be prepended to the column label.
        prefix: Optional prefix to be added between temp_prefix and field_name. If None, only temp_prefix is used.
        field_name: The base field name for the column.

    Returns:
        A formatted column label string combining the prefixes and field name.

    Examples:
        >>> _build_column_label("joined__", "articles_", "title")
        "joined__articles_title"

        >>> _build_column_label("joined__", None, "id")
        "joined__id"
    """
    if prefix:
        return f"{temp_prefix}{prefix}{field_name}"
    else:
        return f"{temp_prefix}{field_name}"


def _extract_schema_columns(
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
        >>> columns = _extract_schema_columns(Author, schema, mapper, "author_", True, "joined__")
        >>> # Returns [Author.id.label("joined__author_id"), Author.name.label("joined__author_name"), ...]
    """
    columns = []
    for field in schema.model_fields.keys():
        if hasattr(model_or_alias, field) and field not in mapper.relationships:
            column = getattr(model_or_alias, field)
            if prefix is not None or use_temporary_prefix:
                column_label = _build_column_label(temp_prefix, prefix, field)
                column = column.label(column_label)
            columns.append(column)
    return columns


def _extract_all_columns(
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
        >>> columns = _extract_all_columns(User, mapper, "user_", True, "joined__")
        >>> # Returns [User.id.label("joined__user_id"), User.name.label("joined__user_name"), ...]
    """
    columns = []
    for prop in mapper.column_attrs:
        column = getattr(model_or_alias, prop.key)
        if prefix is not None or use_temporary_prefix:
            column_label = _build_column_label(temp_prefix, prefix, prop.key)
            column = column.label(column_label)
        columns.append(column)
    return columns


def _extract_matching_columns_from_schema(
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
    _validate_model_has_table(model)

    model_or_alias = alias if alias else model
    temp_prefix = (
        temp_prefix if use_temporary_prefix and temp_prefix is not None else ""
    )
    mapper = inspect(model).mapper

    use_temp_prefix = (
        use_temporary_prefix if use_temporary_prefix is not None else False
    )
    if schema:
        return _extract_schema_columns(
            model_or_alias, schema, mapper, prefix, use_temp_prefix, temp_prefix
        )
    else:
        return _extract_all_columns(
            model_or_alias, mapper, prefix, use_temp_prefix, temp_prefix
        )


def _auto_detect_join_condition(
    base_model: ModelType,
    join_model: ModelType,
) -> Optional[ColumnElement]:
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
    _validate_model_has_table(base_model)
    _validate_model_has_table(join_model)

    inspector = inspect(base_model)
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

        if join_on is None:  # pragma: no cover
            raise ValueError(
                "Could not automatically determine join condition. Please provide join_on."
            )
    else:  # pragma: no cover
        raise ValueError("Could not automatically get model columns.")

    return join_on


def _handle_one_to_one(
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


def _handle_one_to_many(
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


def _sort_nested_list(
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
        >>> _sort_nested_list([{"id": 2, "name": "B"}, {"id": 1, "name": "A"}], "name")
        [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]

        Sorting by multiple columns with different orders:
        >>> _sort_nested_list([{"id": 1, "name": "A"}, {"id": 2, "name": "A"}], ["name", "id"], ["asc", "desc"])
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


def _get_nested_key_for_join(join: JoinConfig) -> str:
    """
    Determines the nested key name for a join configuration in the result data structure.

    This function extracts the appropriate key name that will be used to nest joined data
    in the final result. It prioritizes the custom join_prefix if provided, otherwise
    falls back to the model's table name.

    Args:
        join: The JoinConfig instance containing join configuration details.

    Returns:
        The string key name to be used for nesting the joined data.

    Examples:
        >>> join_config = JoinConfig(model=Article, join_prefix="articles_")
        >>> _get_nested_key_for_join(join_config)
        "articles"

        >>> join_config = JoinConfig(model=Article)  # No prefix specified
        >>> _get_nested_key_for_join(join_config)
        "articles"  # Uses model.__tablename__
    """
    return (
        join.join_prefix.rstrip("_") if join.join_prefix else join.model.__tablename__
    )


def _process_joined_field(
    nested_data: dict[str, Any],
    join: JoinConfig,
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
        join: The JoinConfig instance defining the join relationship type and configuration.
        nested_field: The name of the field being processed from the joined table.
        value: The value of the field being processed.

    Returns:
        The updated nested data dictionary with the processed field added.

    Examples:
        >>> nested_data = {"id": 1, "title": "Test"}
        >>> join_config = JoinConfig(model=Article, relationship_type="one-to-many")
        >>> result = _process_joined_field(nested_data, join_config, "title", "Article 1")
        >>> # Returns updated nested_data with article data nested appropriately
    """
    nested_key = _get_nested_key_for_join(join)

    if join.relationship_type == "one-to-many":
        return _handle_one_to_many(nested_data, nested_key, nested_field, value)
    else:
        return _handle_one_to_one(nested_data, nested_key, nested_field, value)


def _process_data_fields(
    data: dict,
    join_definitions: list[JoinConfig],
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
        join_definitions: List of JoinConfig instances defining how to identify and nest joined data.
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
                nested_data = _process_joined_field(
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


def _cleanup_null_joins(
    nested_data: dict[str, Any], join_definitions: list[JoinConfig]
) -> dict[str, Any]:
    """
    Cleans up nested join data by handling null primary keys and applying sorting configurations.

    This function performs post-processing on nested join data to:
    1. Remove or replace entries with null primary keys (indicating no actual joined data)
    2. Apply sorting to one-to-many relationships when sort configurations are specified
    3. Convert one-to-one relationships with null primary keys to None

    Args:
        nested_data: The nested data dictionary containing organized joined data.
        join_definitions: List of JoinConfig instances with sorting and relationship configurations.

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
        join_primary_key = _get_primary_key(join.model)
        nested_key = _get_nested_key_for_join(join)

        if join.relationship_type == "one-to-many" and nested_key in nested_data:
            if isinstance(nested_data.get(nested_key, []), list):
                if any(
                    item[join_primary_key] is None for item in nested_data[nested_key]
                ):
                    nested_data[nested_key] = []
                elif join.sort_columns and nested_data[nested_key]:
                    nested_data[nested_key] = _sort_nested_list(
                        nested_data[nested_key], join.sort_columns, join.sort_orders
                    )

        if nested_key in nested_data and isinstance(nested_data[nested_key], dict):
            if (
                join_primary_key in nested_data[nested_key]
                and nested_data[nested_key][join_primary_key] is None
            ):
                nested_data[nested_key] = None

    return nested_data


def _nest_join_data(
    data: dict,
    join_definitions: list[JoinConfig],
    temp_prefix: str = "joined__",
    nested_data: Optional[dict[str, Any]] = None,
) -> dict:
    """
    Nests joined data based on join definitions provided. This function processes the input `data` dictionary, identifying keys
    that correspond to joined tables using the provided `join_definitions` and nest them under their respective table keys.

    Args:
        data: The flat dictionary containing data with potentially prefixed keys from joined tables.
        join_definitions: A list of `JoinConfig` instances defining the join configurations, including prefixes.
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

    nested_data = _process_data_fields(data, join_definitions, temp_prefix, nested_data)
    nested_data = _cleanup_null_joins(nested_data, join_definitions)

    assert nested_data is not None, "Couldn't nest the data."
    return nested_data


def _initialize_pre_nested_data(
    base_primary_key: str,
    data: Sequence[Union[dict, BaseModel]],
) -> dict:
    """Initialize the pre-nested data dictionary with base records."""
    pre_nested_data = {}
    for row in data:
        if isinstance(row, BaseModel):
            new_row = row.model_dump()
        else:
            new_row = dict(row)

        primary_key_value = new_row[base_primary_key]
        if primary_key_value not in pre_nested_data:
            pre_nested_data[primary_key_value] = new_row

    return pre_nested_data


def _deduplicate_and_sort_join_items(
    existing_items: set,
    value: list,
    join_primary_key_names: list[str],
    join_config: JoinConfig,
    target_list: list,
) -> None:
    """Deduplicate join items and apply sorting if specified."""
    for item in value:
        item_composite_key = _create_composite_key(item, join_primary_key_names)
        if item_composite_key not in existing_items:
            target_list.append(item)
            existing_items.add(item_composite_key)

    if join_config.sort_columns and target_list:
        target_list[:] = _sort_nested_list(
            target_list, join_config.sort_columns, join_config.sort_orders
        )


def _process_one_to_many_join(
    join_config: JoinConfig,
    data: Sequence[Union[dict, BaseModel]],
    pre_nested_data: dict,
    base_primary_key: str,
    join_primary_key: str,
    join_primary_key_names: list[str],
    join_prefix: str,
) -> None:
    """Process one-to-many join relationships."""
    for row in data:
        row_dict = row if isinstance(row, dict) else row.model_dump()
        primary_key_value = row_dict[base_primary_key]

        if join_prefix in row_dict:
            value = row_dict[join_prefix]
            if isinstance(value, list):
                if any(
                    item[join_primary_key] is None for item in value
                ):  # pragma: no cover
                    pre_nested_data[primary_key_value][join_prefix] = []
                else:
                    existing_items = {
                        _create_composite_key(item, join_primary_key_names)
                        for item in pre_nested_data[primary_key_value][join_prefix]
                    }
                    _deduplicate_and_sort_join_items(
                        existing_items,
                        value,
                        join_primary_key_names,
                        join_config,
                        pre_nested_data[primary_key_value][join_prefix],
                    )


def _process_one_to_one_join(
    data: Sequence[Union[dict, BaseModel]],
    pre_nested_data: dict,
    base_primary_key: str,
    join_primary_key: str,
    join_prefix: str,
) -> None:
    """Process one-to-one join relationships."""
    for row in data:
        row_dict = row if isinstance(row, dict) else row.model_dump()
        primary_key_value = row_dict[base_primary_key]

        if join_prefix in row_dict:
            value = row_dict[join_prefix]
            if isinstance(value, dict) and value.get(join_primary_key) is None:
                pre_nested_data[primary_key_value][join_prefix] = None
            elif isinstance(value, dict):
                pre_nested_data[primary_key_value][join_prefix] = value


def _validate_schema_compatibility(
    joins_config: Sequence[JoinConfig],
    schema_to_select: type[SelectSchemaType],
) -> None:
    """Validate that join prefixes are compatible with schema fields."""
    schema_fields = set(schema_to_select.model_fields.keys())
    for join_config in joins_config:
        if join_config.join_prefix:
            join_key = join_config.join_prefix.rstrip("_")
            if join_key not in schema_fields:
                raise ValueError(
                    f"join_prefix '{join_config.join_prefix}' creates key '{join_key}' "
                    f"which is not a field in schema {schema_to_select.__name__}. "
                    f"Available fields: {sorted(schema_fields)}. "
                    f"Either change join_prefix to match a schema field or use return_as_model=False."
                )


def _convert_to_pydantic_models(
    nested_data: list,
    schema_to_select: type[SelectSchemaType],
    nested_schema_to_select: Optional[dict[str, type[SelectSchemaType]]],
) -> list:
    """Convert nested data to Pydantic models."""
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
                    else:  # pragma: no cover
                        item[prefix_key] = (
                            nested_schema(**item[prefix_key])
                            if item[prefix_key] is not None
                            else None
                        )

        converted_data.append(schema_to_select(**item))
    return converted_data


def _nest_multi_join_data(
    base_primary_key: str,
    data: Sequence[Union[dict, BaseModel]],
    joins_config: Sequence[JoinConfig],
    return_as_model: bool = False,
    schema_to_select: Optional[type[SelectSchemaType]] = None,
    nested_schema_to_select: Optional[dict[str, type[SelectSchemaType]]] = None,
) -> Sequence[Union[dict, SelectSchemaType]]:
    """
    Nests joined data based on join definitions provided for multiple records. This function processes the input list of
    dictionaries, identifying keys that correspond to joined tables using the provided `joins_config`, and nests them
    under their respective table keys.

    Args:
        base_primary_key: The primary key of the base model.
        data: The list of dictionaries containing the records with potentially nested data.
        joins_config: The list of join configurations containing the joined model classes and related settings.
        schema_to_select: Pydantic schema for selecting specific columns from the primary model. Used for converting
                          dictionaries back to Pydantic models.
        return_as_model: If `True`, converts the fetched data to Pydantic models based on `schema_to_select`. Defaults to `False`.
        nested_schema_to_select: A dictionary mapping join prefixes to their corresponding Pydantic schemas.

    Returns:
        Sequence[Union[dict, SelectSchemaType]]: A list of dictionaries with nested structures for joined table data or Pydantic models.

    Example:

        Input:

        ```python
        data = [
            {'id': 1, 'title': 'Test Author', 'articles': [{'id': 1, 'title': 'Article 1', 'author_id': 1}]},
            {'id': 2, 'title': 'Test Author 2', 'articles': [{'id': 2, 'title': 'Article 2', 'author_id': 2}]},
            {'id': 2, 'title': 'Test Author 2', 'articles': [{'id': 3, 'title': 'Article 3', 'author_id': 2}]},
            {'id': 3, 'title': 'Test Author 3', 'articles': [{'id': None, 'title': None, 'author_id': None}]},
        ]

        joins_config = [
            JoinConfig(model=Article, join_prefix='articles_', relationship_type='one-to-many')
        ]
        ```

        Output:

        ```json
        [
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
            },
            {
                'id': 2,
                'title': 'Test Author 2',
                'articles': [
                    {
                        'id': 2,
                        'title': 'Article 2',
                        'author_id': 2
                    },
                    {
                        'id': 3,
                        'title': 'Article 3',
                        'author_id': 2
                    }
                ]
            },
            {
                'id': 3,
                'title': 'Test Author 3',
                'articles': []
            }
        ]
        ```
    """
    pre_nested_data = _initialize_pre_nested_data(base_primary_key, data)

    for join_config in joins_config:
        join_primary_key: str = _get_primary_key(join_config.model)  # type: ignore[assignment]
        join_primary_key_names = _get_primary_key_names(join_config.model)
        join_prefix: str = (
            join_config.join_prefix.rstrip("_")
            if join_config.join_prefix
            else join_config.model.__tablename__
        )

        if join_config.relationship_type == "one-to-many":
            _process_one_to_many_join(
                join_config,
                data,
                pre_nested_data,
                base_primary_key,
                join_primary_key,
                join_primary_key_names,
                join_prefix,
            )
        else:  # pragma: no cover
            _process_one_to_one_join(
                data,
                pre_nested_data,
                base_primary_key,
                join_primary_key,
                join_prefix,
            )

    nested_data: list = list(pre_nested_data.values())

    if return_as_model:
        if not schema_to_select:  # pragma: no cover
            raise ValueError(
                "schema_to_select must be provided when return_as_model is True."
            )

        _validate_schema_compatibility(joins_config, schema_to_select)
        return _convert_to_pydantic_models(
            nested_data, schema_to_select, nested_schema_to_select
        )

    return nested_data


def _handle_null_primary_key_multi_join(
    data: list[Union[dict[str, Any], SelectSchemaType]],
    join_definitions: list[JoinConfig],
) -> list[Union[dict[str, Any], SelectSchemaType]]:
    for item in data:
        item_dict = item if isinstance(item, dict) else item.model_dump()

        for join in join_definitions:
            join_prefix = join.join_prefix or ""
            nested_key = (
                join_prefix.rstrip("_") if join_prefix else join.model.__tablename__
            )

            if nested_key in item_dict and isinstance(item_dict[nested_key], dict):
                join_primary_key = _get_primary_key(join.model)

                primary_key = join_primary_key
                if join_primary_key:
                    if (
                        primary_key in item_dict[nested_key]
                        and item_dict[nested_key][primary_key] is None
                    ):  # pragma: no cover
                        item_dict[nested_key] = None

        if isinstance(item, BaseModel):
            for key, value in item_dict.items():
                setattr(item, key, value)

    return data
