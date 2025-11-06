# Paginated Module Reference

!!! warning "Deprecated"
    The `fastcrud.paginated` module is deprecated as of version 0.18.0 and will be removed in the next major version. Please import pagination utilities directly from `fastcrud` instead:
    
    ```python
    # Old (deprecated)
    from fastcrud.paginated import PaginatedListResponse, PaginatedRequestQuery
    
    # New (recommended)
    from fastcrud import PaginatedListResponse, PaginatedRequestQuery
    ```

`paginated` is a utility module for offset pagination related functions. The functionality has been moved to the core module for better organization.

## Core Pagination Module

The pagination utilities are now consolidated in a single core module:

### Pagination Module

::: fastcrud.core.pagination
    rendering:
      show_if_no_docstring: true

## Backward Compatibility

For backward compatibility, the original imports still work but will issue deprecation warnings:

::: fastcrud.paginated
    rendering:
      show_if_no_docstring: true
