"""
Database operations engine.

This module provides centralized database operation utilities for FastCRUD,
including common patterns for executing queries, handling transactions,
and processing results.
"""

from .executor import DatabaseExecutor
from .transaction import TransactionManager

__all__ = ["DatabaseExecutor", "TransactionManager"]
