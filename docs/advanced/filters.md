# Advanced Filtering

The `_parse_filters` method in FastCRUD supports complex filtering operations including OR and NOT conditions. These filters are used internally when you call methods like `get`, `get_multi`, `update`, `delete`, etc., on a `FastCRUD` instance.

When creating API endpoints using `crud_router` or `EndpointCreator`, you can expose these filtering capabilities to your API users. This is often done for the "read multiple items" endpoint.

## Configuring Filters for Endpoints with `FilterConfig`

The `FilterConfig` class allows you to define which filters are available for an endpoint, their default values, and how they are presented in the API documentation. You pass a `FilterConfig` instance to the `filter_config` parameter of `crud_router` or `EndpointCreator`.

**Example:**

```python
from fastcrud import crud_router, FilterConfig
from fastapi import FastAPI
# Assuming User model, CreateUserSchema, UpdateUserSchema, and async_session are defined

app = FastAPI()

user_router = crud_router(
    session=async_session,
    model=User,
    create_schema=CreateUserSchema,
    update_schema=UpdateUserSchema,
    # Configure filters: 'id' (no default), 'name' (default 'john doe'), 'age__gt' (no default)
    filter_config=FilterConfig(
        filters={
            "id": None,  # Field 'id', operator 'eq' (default), no default value
            "name": "john doe", # Field 'name', operator 'eq' (default), default value "john doe"
            "age__gt": None  # Field 'age', operator 'gt', no default value
        }
    )
)

app.include_router(user_router, prefix="/users")
```

In this example:
- The `/users` (read multiple) endpoint will accept query parameters `id`, `name`, and `age__gt`.
- `id` and `age__gt` are optional.
- `name` is optional and defaults to "john doe" if not provided.

The keys in the `filters` dictionary of `FilterConfig` are strings in the format `'field_name__operator'` or just `'field_name'` (which defaults to the `eq` operator).

!!! note
    Filter strings like `'field_name__operator'` provided in `FilterConfig` are validated at runtime when `EndpointCreator` (used by `crud_router`) is initialized. If a field name or operator is invalid, a `ValueError` will be raised.
    However, due to Python's typing limitations for such dynamic dictionary keys, IDEs may not provide full static type-checking or autocompletion for these filter strings.

## Basic Filter Usage (Directly with FastCRUD methods)

Filters are specified as keyword arguments in the format `field_name__operator=value`:

```python
# Simple equality filter
results = await crud.get_multi(db, name="John")

# Comparison operators
results = await crud.get_multi(db, age__gt=18)
```

## OR Operations

### Single Field OR

Use the `__or` suffix to apply multiple conditions to the same field with OR logic:

```python
# Find users aged under 18 OR over 65
results = await crud.get_multi(
    db,
    age__or={
        "lt": 18,
        "gt": 65
    }
)
# Generates: WHERE age < 18 OR age > 65
```

### Multi-Field OR

Use the special `_or` parameter to apply OR conditions across multiple different fields:

```python
# Find users with name containing 'john' OR email containing 'john'
results = await crud.get_multi(
    db,
    _or={
        "name__ilike": "%john%",
        "email__ilike": "%john%"
    }
)
# Generates: WHERE name ILIKE '%john%' OR email ILIKE '%john%'
```

This is particularly useful for implementing search functionality across multiple fields.

## NOT Operations

Use the `__not` suffix to negate multiple conditions on the same field:

```python
# Find users NOT aged 20 AND NOT between 30-40
results = await crud.get_multi(
    db,
    age__not={
        "eq": 20,
        "between": (30, 40)
    }
)
# Generates: WHERE NOT age = 20 AND NOT (age BETWEEN 30 AND 40)
```

## Supported Operators and Expected Value Types

Below is a list of supported filter operators and the expected Python type for their values when using them with `FastCRUD` methods or defining them in `FilterConfig`.

| Operator        | Description                      | Expected Value Type(s)              | Example Usage (in `get_multi`)        |
|-----------------|----------------------------------|-------------------------------------|---------------------------------------|
| `eq`            | Equal to                         | `Any` (str, int, bool, etc.)        | `name="John"`                         |
| `ne`            | Not equal to                     | `Any`                               | `status__ne="archived"`               |
| `gt`            | Greater than                     | `Any` (numeric/date types)          | `age__gt=18`                          |
| `lt`            | Less than                        | `Any` (numeric/date types)          | `price__lt=100.0`                     |
| `gte`           | Greater than or equal to         | `Any` (numeric/date types)          | `stock__gte=0`                        |
| `lte`           | Less than or equal to            | `Any` (numeric/date types)          | `created_at__lte=datetime.now()`      |
| `is`            | Is (identity check)              | `bool`, `None`                      | `is_active__is=True`                  |
| `is_not`        | Is not (identity check)          | `bool`, `None`                      | `deleted_at__is_not=None`             |
| `like`          | SQL LIKE (case-sensitive)        | `str` (e.g., `"%pattern%"`)         | `name__like="J%"`                     |
| `notlike`       | SQL NOT LIKE (case-sensitive)    | `str`                               | `name__notlike="J%"`                  |
| `ilike`         | SQL ILIKE (case-insensitive)     | `str` (e.g., `"%pattern%"`)         | `email__ilike="%@example.com"`        |
| `notilike`      | SQL NOT ILIKE (case-insensitive) | `str`                               | `description__notilike="%spam%"`      |
| `startswith`    | Starts with                      | `str`                               | `sku__startswith="PROD-"`             |
| `endswith`      | Ends with                        | `str`                               | `file_type__endswith=".pdf"`          |
| `contains`      | Contains                         | `str`                               | `tags__contains="urgent"`             |
| `match`         | Database-specific match          | `str`                               | `title__match="search query"`         |
| `in`            | In a collection                  | `list`, `tuple`, `set`              | `status__in=["pending", "active"]`    |
| `not_in`        | Not in a collection              | `list`, `tuple`, `set`              | `category__not_in=["deprecated"]`     |
| `between`       | Between two values (inclusive)   | `tuple` or `list` of two elements   | `age__between=(18, 65)`               |
| `or` (suffix)   | Logical OR on the same field     | `dict` (operator: value pairs)      | `age__or={"lt": 18, "gt": 65}`        |
| `not` (suffix)  | Logical NOT on the same field    | `dict` (operator: value pairs)      | `age__not={"eq": 20, "gt": 30}`       |
| `_or` (special) | Logical OR across different fields| `dict` (filter_string: value pairs)| `_or={"name__eq": "A", "id__gt": 10}` |

**Note on `_or` (special parameter):**
The `_or` parameter is used at the top level of keyword arguments passed to `FastCRUD` methods (like `get_multi`). It is not an operator suffix like `__or`.

## Examples of Direct Filter Usage

```python
# Complex age filtering
results = await crud.get_multi(
    db,
    age__or={
        "between": (20, 30),
        "eq": 18
    },
    status__not={
        "in": ["inactive", "banned"]
    }
)

# Text search with OR conditions on a single field
results = await crud.get_multi(
    db,
    name__or={
        "startswith": "A",
        "endswith": "smith"
    }
)

# Search across multiple fields with the same keyword
keyword = "john"
results = await crud.get_multi(
    db,
    _or={
        "name__ilike": f"%{keyword}%",
        "email__ilike": f"%{keyword}%",
        "phone__ilike": f"%{keyword}%",
        "address__ilike": f"%{keyword}%"
    }
)

# Combining multi-field OR with regular filters
results = await crud.get_multi(
    db,
    is_active=True,  # Regular filter applied to all results
    _or={
        "name__ilike": "%search term%",
        "description__ilike": "%search term%"
    }
)
```

## Error Handling

- Invalid column names raise `ValueError`
- Invalid operators are ignored
- Invalid value types for operators (e.g., non-list for `between`) raise `ValueError`