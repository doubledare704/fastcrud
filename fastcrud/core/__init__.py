"""
FastCRUD Core Module - Centralized utilities for SQLAlchemy model operations.

This module provides the foundational utilities used throughout FastCRUD for:
- Model introspection with caching
- Data processing and transformation
- Join processing and relationship handling
- Field management and schema operations
- Configuration classes for all operations

The core module is designed with performance in mind, using strategic caching
to avoid repeated expensive operations while maintaining clean, functional APIs.
"""

from .introspection import ModelInspector, get_model_inspector
from .join_processing import JoinProcessor, handle_null_primary_key_multi_join

from .introspection import (
    get_primary_key_names,
    get_primary_key_columns,
    get_first_primary_key,
    get_unique_columns,
    get_python_type,
    get_column_types,
    create_composite_key,
    validate_model_has_table,
)

# Data processing
from .data_processing import (
    nest_join_data,
    sort_nested_list,
    handle_one_to_one,
    handle_one_to_many,
    convert_to_pydantic_models,
    build_column_label,
)

# Pagination
from .pagination.helper import compute_offset
from .pagination.response import paginated_response
from .pagination.schemas import (
    PaginatedListResponse,
    ListResponse,
    PaginatedRequestQuery,
    CursorPaginatedRequestQuery,
    create_list_response,
    create_paginated_response,
)

# Field and schema management
from .field_management import (
    create_modified_schema,
    create_auto_field_injector,
    create_dynamic_filters,
    extract_matching_columns_from_schema,
    inject_dependencies,
    apply_model_pk,
    auto_detect_join_condition,
)

# Configuration
from .config import (
    JoinConfig,
    CountConfig,
    CreateConfig,
    UpdateConfig,
    DeleteConfig,
    FilterConfig,
    CRUDMethods,
    validate_joined_filter_path,
)

__all__ = [
    # Core classes
    "ModelInspector",
    "get_model_inspector",
    "JoinProcessor",
    "handle_null_primary_key_multi_join",
    # Introspection functions
    "get_primary_key_names",
    "get_primary_key_columns",
    "get_first_primary_key",
    "get_unique_columns",
    "get_python_type",
    "get_column_types",
    "create_composite_key",
    "validate_model_has_table",
    # Data processing functions
    "nest_join_data",
    "sort_nested_list",
    "handle_one_to_one",
    "handle_one_to_many",
    "convert_to_pydantic_models",
    "build_column_label",
    # Pagination utilities
    "compute_offset",
    "paginated_response",
    "PaginatedListResponse",
    "ListResponse",
    "PaginatedRequestQuery",
    "CursorPaginatedRequestQuery",
    "create_list_response",
    "create_paginated_response",
    # Field management functions
    "create_modified_schema",
    "create_auto_field_injector",
    "create_dynamic_filters",
    "extract_matching_columns_from_schema",
    "inject_dependencies",
    "apply_model_pk",
    "auto_detect_join_condition",
    # Configuration classes
    "JoinConfig",
    "CountConfig",
    "CreateConfig",
    "UpdateConfig",
    "DeleteConfig",
    "FilterConfig",
    "CRUDMethods",
    "validate_joined_filter_path",
]
