# Contributing to FastCRUD

Thank you for your interest in contributing to FastCRUD! This guide will get you started quickly.

## Quick Setup

```sh
# Clone and setup
git clone https://github.com/benavlabs/fastcrud.git
cd fastcrud
uv sync

# Verify installation
uv run pytest
uv run mypy fastcrud
uv run ruff check
```

## Architecture Overview

FastCRUD follows a **six-level dependency hierarchy** that prevents circular dependencies:

```
Level 6: Framework     → fastapi_dependencies.py, endpoint/
Level 5: CRUD          → crud/ (FastCRUD class, validation)
Level 4: Integration   → core/data/formatting.py, core/join_processing.py
Level 3: Orchestration → core/query/, core/data/nesting.py, core/field_management.py
Level 2: Core Logic    → core/config/, core/filtering/, core/data/transforms.py, core/pagination.py
Level 1: Foundation    → core/protocols.py, core/introspection.py, types.py
```

**Key Rules:**
- Each level only imports from lower levels
- Use Protocol interfaces instead of concrete class imports
- Keep framework-specific code in Level 6
- Pure functions go in Level 2 (core/data/transforms.py)

## Before You Code

1. **Understand the dependency hierarchy** - your changes must respect the levels
2. **Use existing patterns** - look at similar code for consistency
3. **Write tests first** - especially for new functionality
4. **Check where your code belongs** - use the architecture guide

## Code Standards

### Import Organization
```python
# Standard library
from typing import Any, Optional

# Third-party  
from fastapi import FastAPI
from sqlalchemy import select

# Local - respect hierarchy levels
from ..core import ModelInspector  # Lower level OK
from .validation import validate   # Same level OK
# from ..crud import FastCRUD      # Higher level - DON'T DO THIS
```

### Use Protocols for Interfaces
```python
# Instead of concrete imports that create circular deps
from ..core.protocols import CRUDInstance

def handle_operation(crud: CRUDInstance):  # Protocol interface
    return crud.get_multi_joined(...)
```

### Where to Put New Code

| Type of Change | Location | Level |
|---------------|----------|-------|
| Pure data transformation | `core/data/transforms.py` | 2 |
| Model introspection | `core/introspection.py` | 1 |
| Filter operators | `core/filtering/` | 2 |
| Query building | `core/query/` | 3 |
| CRUD methods | `crud/fast_crud.py` | 5 |
| FastAPI endpoints | `endpoint/` | 6 |
| Protocol interfaces | `core/protocols.py` | 1 |

## Testing

```sh
# Run tests
uv run pytest

# With coverage
uv run pytest --cov=fastcrud

# Type checking
uv run mypy fastcrud

# Linting
uv run ruff check --fix
uv run ruff format

# All checks
uv run pytest && uv run mypy fastcrud && uv run ruff check
```

## Pull Request Process

1. **Create feature branch**: `git checkout -b feature/your-feature`
2. **Make changes** following the architecture principles
3. **Add tests** for new functionality
4. **Run all checks** (tests, mypy, ruff)
5. **Submit PR** with clear description

## Common Scenarios

### Adding a New CRUD Method
1. Add method to `FastCRUD` class (`crud/fast_crud.py`)
2. Add validation if needed (`crud/validation.py`)
3. Add tests (`tests/test_crud.py`)
4. Update typing and ensure protocol compliance

### Adding a Filter Operator
1. Add operator (`core/filtering/operators.py`)
2. Update processor (`core/filtering/processor.py`)
3. Add validation (`core/filtering/validators.py`)
4. Add tests and documentation

### Protocol-Based Refactoring
When you need to break a circular dependency:
1. Define a Protocol interface (`core/protocols.py`)
2. Replace concrete imports with Protocol
3. Ensure the concrete class satisfies the Protocol
4. Update tests to use Protocol

## Architecture Details

### Data Processing Flow
```
Raw DB Results → Transforms (Level 2) → Nesting (Level 3) → Formatting (Level 4) → Response
```

### Protocol Examples
```python
# In core/protocols.py
class CRUDInstance(Protocol):
    model: Any
    async def get_multi_joined(self, db: Any, **kwargs) -> Any: ...

# Usage in lower levels
def handle_filters(crud: CRUDInstance, filters: dict):
    return crud.get_multi_joined(db, join_filters=filters)
```

### Data Module Organization
```
core/data/
├── transforms.py   # Level 2: Pure functions, no deps
├── nesting.py     # Level 3: Uses introspection
└── formatting.py  # Level 4: Uses join_processing
```

## Performance Guidelines

- **Cache expensive operations** (model introspection is already cached)
- **Use TYPE_CHECKING imports** for type hints that would create circular deps
- **Keep functions pure** when possible (easier to test and reason about)
- **Stream large datasets** instead of loading everything into memory

## Error Prevention

### Avoid Circular Dependencies
```python
# DON'T - creates circular dependency
from ..crud.fast_crud import FastCRUD

# DO - use protocol instead
from ..core.protocols import CRUDInstance
```

### Respect the Hierarchy
```python
# DON'T - Level 2 importing from Level 5
# In core/data/transforms.py
from ...crud.validation import validate_data

# DO - Level 5 importing from Level 2
# In crud/validation.py  
from ..core.data.transforms import transform_data
```

## Need Help?

- **Documentation**: Check the full [Architecture Documentation](docs/architecture.md)
- **Issues**: Create a GitHub issue for bugs/features
- **Discussions**: Use GitHub Discussions for questions

## Code of Conduct

Please follow our [Code of Conduct](CODE_OF_CONDUCT.md) to maintain a welcoming environment.

---

**Quick Reference:**
- Six-level dependency hierarchy (Foundation → Framework)
- Use Protocols for interfaces, avoid circular dependencies
- Pure functions in Level 2, framework code in Level 6
- Test everything, respect existing patterns

Thank you for contributing to FastCRUD! 🚀