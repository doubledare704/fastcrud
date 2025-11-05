"""
SQL Query Builder.

This module provides the main SQLQueryBuilder class that coordinates
query construction with support for filtering, sorting, pagination, and joins.
"""

from typing import Optional, Union, Any
from sqlalchemy import Select, select
from sqlalchemy.sql.elements import ColumnElement

from .sorting import SortProcessor
from .joins import JoinBuilder
from ...types import ModelType


class SQLQueryBuilder:
    """Builds and modifies SQLAlchemy SELECT statements."""

    def __init__(self, model: type[ModelType]):
        """
        Initialize query builder for a specific model.

        Args:
            model: SQLAlchemy model class
        """
        self.model = model
        self.sort_processor = SortProcessor(model)
        self.join_builder = JoinBuilder(model)

    def build_base_select(self, columns: Optional[list[Any]] = None) -> Select:
        """
        Create base SELECT statement.

        Args:
            columns: Optional list of specific columns to select.
                    If None, selects all columns from the model.

        Returns:
            SQLAlchemy SELECT statement

        Example:
            >>> builder = SQLQueryBuilder(User)
            >>> stmt = builder.build_base_select()  # SELECT * FROM users
            >>> stmt = builder.build_base_select([User.id, User.name])  # SELECT id, name FROM users
        """
        if columns:
            return select(*columns)
        else:
            return select(self.model)

    def apply_filters(self, stmt: Select, filters: list[ColumnElement]) -> Select:
        """
        Apply WHERE conditions to statement.

        Args:
            stmt: SQLAlchemy SELECT statement to modify
            filters: List of SQLAlchemy filter conditions

        Returns:
            Modified SELECT statement with WHERE clauses

        Example:
            >>> builder = SQLQueryBuilder(User)
            >>> stmt = builder.build_base_select()
            >>> filters = [User.age > 18, User.is_active == True]
            >>> filtered_stmt = builder.apply_filters(stmt, filters)
        """
        if filters:
            return stmt.where(*filters)
        return stmt

    def apply_sorting(
        self,
        stmt: Select,
        sort_columns: Union[str, list[str]],
        sort_orders: Optional[Union[str, list[str]]] = None,
    ) -> Select:
        """
        Apply ORDER BY to statement.

        Args:
            stmt: SQLAlchemy SELECT statement to modify
            sort_columns: Column name(s) to sort by
            sort_orders: Sort direction(s) - 'asc' or 'desc'

        Returns:
            Modified SELECT statement with ORDER BY clause

        Example:
            >>> builder = SQLQueryBuilder(User)
            >>> stmt = builder.build_base_select()
            >>> sorted_stmt = builder.apply_sorting(stmt, ['name', 'created_at'], ['asc', 'desc'])
        """
        return self.sort_processor.apply_sorting_to_statement(
            stmt, sort_columns, sort_orders
        )

    def apply_pagination(
        self, stmt: Select, offset: int = 0, limit: Optional[int] = None
    ) -> Select:
        """
        Apply OFFSET and LIMIT to statement.

        Args:
            stmt: SQLAlchemy SELECT statement to modify
            offset: Number of rows to skip (default: 0)
            limit: Maximum number of rows to return (default: None - no limit)

        Returns:
            Modified SELECT statement with OFFSET and/or LIMIT clauses

        Example:
            >>> builder = SQLQueryBuilder(User)
            >>> stmt = builder.build_base_select()
            >>> paginated_stmt = builder.apply_pagination(stmt, offset=20, limit=10)
        """
        if offset:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        return stmt

    def prepare_joins(self, stmt: Select, joins_config: list[Any]) -> Select:
        """
        Apply joins to statement.

        Args:
            stmt: SQLAlchemy SELECT statement to modify
            joins_config: List of join configurations

        Returns:
            Modified SELECT statement with JOIN clauses

        Raises:
            NotImplementedError: Join logic will be implemented in future phase

        Example:
            >>> builder = SQLQueryBuilder(User)
            >>> stmt = builder.build_base_select()
            >>> joined_stmt = builder.prepare_joins(stmt, [join_config])
        """
        return self.join_builder.prepare_joins(stmt, joins_config)
