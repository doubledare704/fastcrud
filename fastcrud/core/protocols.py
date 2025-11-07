"""
Protocol interfaces for FastCRUD components.

This module defines Protocol interfaces that provide type-safe contracts
for breaking circular dependencies and enabling future extensibility.
These protocols will serve as the foundation for abstract base classes
when multi-ORM support is implemented.
"""

from typing import (
    Protocol,
    Any,
    Optional,
    Union,
    List,
    Dict,
    overload,
    Literal,
    TYPE_CHECKING,
)

if TYPE_CHECKING:
    from ..types import SelectSchemaType, GetMultiResponseModel, GetMultiResponseDict


class CRUDInstance(Protocol):
    """
    Protocol for CRUD instance operations.

    This protocol defines the interface that CRUD instances must implement
    for delegation and interaction with other components.
    """

    model: Any

    @overload
    async def get_multi_joined(
        self,
        db: Any,
        schema_to_select: "type[SelectSchemaType]",
        return_as_model: Literal[True],
        join_model: Optional[Any] = None,
        join_on: Optional[Any] = None,
        join_prefix: Optional[str] = None,
        join_schema_to_select: Optional[Any] = None,
        join_type: str = "left",
        alias: Optional[Any] = None,
        join_filters: Optional[Dict] = None,
        nest_joins: bool = False,
        offset: int = 0,
        limit: Optional[int] = None,
        sort_columns: Optional[Union[str, List[str]]] = None,
        sort_orders: Optional[Union[str, List[str]]] = None,
        joins_config: Optional[List[Any]] = None,
        counts_config: Optional[List[Any]] = None,
        return_total_count: bool = True,
        relationship_type: Optional[str] = None,
        nested_schema_to_select: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> "GetMultiResponseModel[SelectSchemaType]": ...

    @overload
    async def get_multi_joined(
        self,
        db: Any,
        schema_to_select: None = None,
        return_as_model: Literal[False] = False,
        join_model: Optional[Any] = None,
        join_on: Optional[Any] = None,
        join_prefix: Optional[str] = None,
        join_schema_to_select: Optional[Any] = None,
        join_type: str = "left",
        alias: Optional[Any] = None,
        join_filters: Optional[Dict] = None,
        nest_joins: bool = False,
        offset: int = 0,
        limit: Optional[int] = None,
        sort_columns: Optional[Union[str, List[str]]] = None,
        sort_orders: Optional[Union[str, List[str]]] = None,
        joins_config: Optional[List[Any]] = None,
        counts_config: Optional[List[Any]] = None,
        return_total_count: bool = True,
        relationship_type: Optional[str] = None,
        nested_schema_to_select: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> "GetMultiResponseDict": ...

    @overload
    async def get_multi_joined(
        self,
        db: Any,
        *,
        schema_to_select: Optional[Any] = None,
        return_as_model: bool = False,
        join_model: Optional[Any] = None,
        join_on: Optional[Any] = None,
        join_prefix: Optional[str] = None,
        join_schema_to_select: Optional[Any] = None,
        join_type: str = "left",
        alias: Optional[Any] = None,
        join_filters: Optional[Dict] = None,
        nest_joins: bool = False,
        offset: int = 0,
        limit: Optional[int] = None,
        sort_columns: Optional[Union[str, List[str]]] = None,
        sort_orders: Optional[Union[str, List[str]]] = None,
        joins_config: Optional[List[Any]] = None,
        counts_config: Optional[List[Any]] = None,
        return_total_count: bool = True,
        relationship_type: Optional[str] = None,
        nested_schema_to_select: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Union["GetMultiResponseModel[SelectSchemaType]", "GetMultiResponseDict"]: ...

    async def get_multi_joined(
        self,
        db: Any,
        schema_to_select: Optional[Any] = None,
        return_as_model: bool = False,
        join_model: Optional[Any] = None,
        join_on: Optional[Any] = None,
        join_prefix: Optional[str] = None,
        join_schema_to_select: Optional[Any] = None,
        join_type: str = "left",
        alias: Optional[Any] = None,
        join_filters: Optional[Dict] = None,
        nest_joins: bool = False,
        offset: int = 0,
        limit: Optional[int] = None,
        sort_columns: Optional[Union[str, List[str]]] = None,
        sort_orders: Optional[Union[str, List[str]]] = None,
        joins_config: Optional[List[Any]] = None,
        counts_config: Optional[List[Any]] = None,
        return_total_count: bool = True,
        relationship_type: Optional[str] = None,
        nested_schema_to_select: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Union["GetMultiResponseModel[SelectSchemaType]", "GetMultiResponseDict"]: ...


class ModelIntrospector(Protocol):
    """
    Protocol for model introspection operations.

    This protocol defines the interface for extracting metadata
    from ORM models in a framework-agnostic way.
    """

    def get_primary_keys(self, model: Any) -> List[str]:
        """Get list of primary key column names for a model."""
        ...

    def get_column_names(self, model: Any) -> List[str]:
        """Get list of all column names for a model."""
        ...

    def get_column_types(self, model: Any) -> Dict[str, Any]:
        """Get mapping of column names to their types."""
        ...

    def get_relationships(self, model: Any) -> Dict[str, Any]:
        """Get relationship information for a model."""
        ...


class DataProcessor(Protocol):
    """
    Protocol for data processing operations.

    This protocol defines the interface for processing and transforming
    data structures, particularly for joined data scenarios.
    """

    def process_joined_data(
        self,
        data_list: List[Dict],
        join_definitions: List[Any],
        nest_joins: bool,
        primary_model: Any,
    ) -> Optional[Dict[str, Any]]:
        """Process joined data for complex relationship scenarios."""
        ...


class FilterProcessor(Protocol):
    """
    Protocol for filter processing operations.

    This protocol defines the interface for parsing and applying
    filters to database queries.
    """

    def parse_filters(
        self,
        model: Optional[Any] = None,
        **kwargs: Any,
    ) -> List[Any]:
        """Parse filter arguments into database query conditions."""
        ...

    def separate_joined_filters(
        self,
        **kwargs: Any,
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """Separate regular filters from joined table filters."""
        ...


class QueryBuilder(Protocol):
    """
    Protocol for query building operations.

    This protocol defines the interface for building database queries
    with support for filters, sorting, and pagination.
    """

    def build_base_select(self, columns: Optional[List[Any]] = None) -> Any:
        """Build a base SELECT statement."""
        ...

    def apply_filters(self, stmt: Any, filters: List[Any]) -> Any:
        """Apply WHERE conditions to a statement."""
        ...

    def apply_sorting(
        self,
        stmt: Any,
        sort_columns: Union[str, List[str]],
        sort_orders: Optional[Union[str, List[str]]] = None,
    ) -> Any:
        """Apply ORDER BY to a statement."""
        ...

    def apply_pagination(
        self,
        stmt: Any,
        offset: int = 0,
        limit: Optional[int] = None,
    ) -> Any:
        """Apply OFFSET and LIMIT to a statement."""
        ...


class ResponseFormatter(Protocol):
    """
    Protocol for response formatting operations.

    This protocol defines the interface for formatting database
    query results into standardized response structures.
    """

    def format_single_response(
        self,
        data: Any,
        schema_to_select: Optional[Any] = None,
        return_as_model: bool = False,
    ) -> Union[Dict, Any]:
        """Format single record response."""
        ...

    def format_multi_response(
        self,
        data: List[Any],
        schema_to_select: Optional[Any] = None,
        return_as_model: bool = False,
    ) -> List[Any]:
        """Format multiple records response."""
        ...

    async def format_joined_response(
        self,
        primary_model: Any,
        raw_data: List[Dict],
        config: Dict[str, Any],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Format response for joined query results."""
        ...


class DatabaseAdapter(Protocol):
    """
    Protocol for database-specific operations.

    This protocol defines the interface for database dialect-specific
    operations like upserts that vary between database engines.
    """

    async def upsert_multiple(
        self,
        model_class: Any,
        instances: List[Any],
        filters: Optional[List[Any]] = None,
        update_override: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> tuple[Any, List[Dict]]:
        """Execute database-specific upsert operation."""
        ...

    def supports_returning_clause(self) -> bool:
        """Check if database supports RETURNING clause."""
        ...

    def supports_upsert(self) -> bool:
        """Check if database supports native upsert operations."""
        ...

    def get_dialect_name(self) -> str:
        """Get the database dialect name."""
        ...


class ValidationProcessor(Protocol):
    """
    Protocol for validation operations.

    This protocol defines the interface for validating data and
    parameters in CRUD operations.
    """

    async def validate_update_delete_operation(
        self,
        count_func: Any,
        db: Any,
        allow_multiple: bool,
        operation_name: str,
        **kwargs: Any,
    ) -> int:
        """Validate update/delete operations."""
        ...

    def validate_pagination_params(
        self,
        offset: int,
        limit: Optional[int],
    ) -> None:
        """Validate pagination parameters."""
        ...

    def validate_joined_query_params(
        self,
        primary_model: Any,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Validate joined query parameters."""
        ...
