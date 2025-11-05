"""
Backward compatibility module for paginated utilities.

.. deprecated:: 0.19.0
   The `fastcrud.paginated` module is deprecated and will be removed in the next major version.
   Please import pagination utilities directly from `fastcrud` instead:

   .. code-block:: python

       # Old (deprecated)
       from fastcrud.paginated import PaginatedListResponse, PaginatedRequestQuery

       # New (recommended)
       from fastcrud import PaginatedListResponse, PaginatedRequestQuery
"""

import warnings

from .core.pagination.response import paginated_response
from .core.pagination.helper import compute_offset
from .core.pagination.schemas import (
    PaginatedListResponse,
    ListResponse,
    PaginatedRequestQuery,
    CursorPaginatedRequestQuery,
    create_list_response,
    create_paginated_response,
)

warnings.warn(
    "The 'fastcrud.paginated' module is deprecated and will be removed in the next major version. "
    "Please import pagination utilities directly from 'fastcrud' instead. "
    "For example: 'from fastcrud import PaginatedListResponse, PaginatedRequestQuery'",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "PaginatedListResponse",
    "ListResponse",
    "PaginatedRequestQuery",
    "CursorPaginatedRequestQuery",
    "create_list_response",
    "create_paginated_response",
    "paginated_response",
    "compute_offset",
]
