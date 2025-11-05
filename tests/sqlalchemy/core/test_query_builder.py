"""
Tests for the SQL Query Building Engine with SQLAlchemy models.

This module tests the query building functionality including statement creation,
filtering, sorting, pagination, and error handling.
"""

import pytest
from sqlalchemy import Select, select
from sqlalchemy.exc import ArgumentError

from fastcrud.core.query import SQLQueryBuilder, SortProcessor, JoinBuilder
from tests.sqlalchemy.conftest import ModelTest, TierModel


class TestSQLQueryBuilder:
    """Test cases for SQLQueryBuilder functionality."""

    def test_init(self):
        """Test SQLQueryBuilder initialization"""
        builder = SQLQueryBuilder(ModelTest)

        assert builder.model == ModelTest
        assert isinstance(builder.sort_processor, SortProcessor)
        assert isinstance(builder.join_builder, JoinBuilder)

    def test_build_base_select_all_columns(self):
        """Test building base SELECT statement for all columns"""
        builder = SQLQueryBuilder(ModelTest)
        stmt = builder.build_base_select()

        assert isinstance(stmt, Select)
        # Should select from the model table
        assert ModelTest in stmt.column_descriptions[0]["entity"].__mro__

    def test_build_base_select_specific_columns(self):
        """Test building base SELECT statement for specific columns"""
        builder = SQLQueryBuilder(ModelTest)
        columns = [ModelTest.id, ModelTest.name]
        stmt = builder.build_base_select(columns)

        assert isinstance(stmt, Select)
        # Should have specific columns selected
        assert len(stmt.selected_columns) == 2

    def test_apply_filters_empty(self):
        """Test applying empty filter list"""
        builder = SQLQueryBuilder(ModelTest)
        stmt = builder.build_base_select()
        filtered_stmt = builder.apply_filters(stmt, [])

        # Should return same statement when no filters
        assert stmt == filtered_stmt

    def test_apply_filters_with_conditions(self):
        """Test applying filter conditions"""
        builder = SQLQueryBuilder(ModelTest)
        stmt = builder.build_base_select()
        filters = [ModelTest.id > 5, ModelTest.name == "Alice"]
        filtered_stmt = builder.apply_filters(stmt, filters)

        assert isinstance(filtered_stmt, Select)
        # Should have WHERE clauses applied
        assert filtered_stmt != stmt

    def test_apply_pagination_offset_only(self):
        """Test pagination with offset only"""
        builder = SQLQueryBuilder(ModelTest)
        stmt = builder.build_base_select()
        paginated_stmt = builder.apply_pagination(stmt, offset=10)

        assert isinstance(paginated_stmt, Select)
        assert paginated_stmt._offset_clause.value == 10
        assert paginated_stmt._limit_clause is None

    def test_apply_pagination_limit_only(self):
        """Test pagination with limit only"""
        builder = SQLQueryBuilder(ModelTest)
        stmt = builder.build_base_select()
        paginated_stmt = builder.apply_pagination(stmt, limit=20)

        assert isinstance(paginated_stmt, Select)
        assert paginated_stmt._limit_clause.value == 20

    def test_apply_pagination_offset_and_limit(self):
        """Test pagination with both offset and limit"""
        builder = SQLQueryBuilder(ModelTest)
        stmt = builder.build_base_select()
        paginated_stmt = builder.apply_pagination(stmt, offset=15, limit=25)

        assert isinstance(paginated_stmt, Select)
        assert paginated_stmt._offset_clause.value == 15
        assert paginated_stmt._limit_clause.value == 25

    def test_apply_pagination_zero_offset(self):
        """Test pagination with zero offset (should not apply offset)"""
        builder = SQLQueryBuilder(ModelTest)
        stmt = builder.build_base_select()
        paginated_stmt = builder.apply_pagination(stmt, offset=0, limit=10)

        assert isinstance(paginated_stmt, Select)
        assert paginated_stmt._offset_clause is None
        assert paginated_stmt._limit_clause.value == 10

    def test_apply_sorting_delegates_to_sort_processor(self):
        """Test that sorting delegates to SortProcessor"""
        builder = SQLQueryBuilder(ModelTest)
        stmt = builder.build_base_select()
        sorted_stmt = builder.apply_sorting(stmt, "name", "asc")

        assert isinstance(sorted_stmt, Select)
        # Should have ORDER BY clause
        assert sorted_stmt != stmt

    def test_prepare_joins_delegates_to_join_builder(self):
        """Test that joins delegate to JoinBuilder"""
        builder = SQLQueryBuilder(ModelTest)
        stmt = builder.build_base_select()

        # Empty joins should return the same statement
        result_stmt = builder.prepare_joins(stmt, [])
        assert result_stmt == stmt

    def test_query_building_chain(self):
        """Test chaining multiple query building operations"""
        builder = SQLQueryBuilder(ModelTest)

        # Build a complex query step by step
        stmt = builder.build_base_select()
        stmt = builder.apply_filters(stmt, [ModelTest.id > 1])
        stmt = builder.apply_sorting(stmt, ["name", "id"], ["asc", "desc"])
        stmt = builder.apply_pagination(stmt, offset=10, limit=20)

        assert isinstance(stmt, Select)
        # Should have all modifications applied
        assert stmt._offset_clause.value == 10
        assert stmt._limit_clause.value == 20


class TestSortProcessor:
    """Test cases for SortProcessor functionality."""

    def test_init(self):
        """Test SortProcessor initialization"""
        processor = SortProcessor(ModelTest)
        assert processor.model == ModelTest

    def test_apply_sorting_empty_columns(self):
        """Test sorting with empty sort_columns"""
        processor = SortProcessor(ModelTest)
        stmt = select(ModelTest)
        sorted_stmt = processor.apply_sorting_to_statement(stmt, [])

        # Should return original statement
        assert stmt == sorted_stmt

    def test_apply_sorting_none_columns(self):
        """Test sorting with None sort_columns"""
        processor = SortProcessor(ModelTest)
        stmt = select(ModelTest)
        sorted_stmt = processor.apply_sorting_to_statement(stmt, None)

        # Should return original statement
        assert stmt == sorted_stmt

    def test_apply_sorting_single_column_string(self):
        """Test sorting with single column as string"""
        processor = SortProcessor(ModelTest)
        stmt = select(ModelTest)
        sorted_stmt = processor.apply_sorting_to_statement(stmt, "name")

        assert isinstance(sorted_stmt, Select)
        assert sorted_stmt != stmt

    def test_apply_sorting_single_column_list(self):
        """Test sorting with single column as list"""
        processor = SortProcessor(ModelTest)
        stmt = select(ModelTest)
        sorted_stmt = processor.apply_sorting_to_statement(stmt, ["name"])

        assert isinstance(sorted_stmt, Select)
        assert sorted_stmt != stmt

    def test_apply_sorting_multiple_columns(self):
        """Test sorting with multiple columns"""
        processor = SortProcessor(ModelTest)
        stmt = select(ModelTest)
        sorted_stmt = processor.apply_sorting_to_statement(
            stmt, ["name", "id"], ["asc", "desc"]
        )

        assert isinstance(sorted_stmt, Select)
        assert sorted_stmt != stmt

    def test_apply_sorting_default_order(self):
        """Test sorting with default order (should be asc)"""
        processor = SortProcessor(ModelTest)
        stmt = select(ModelTest)
        sorted_stmt = processor.apply_sorting_to_statement(stmt, "name")

        assert isinstance(sorted_stmt, Select)
        # Default should be ascending

    def test_apply_sorting_explicit_asc(self):
        """Test sorting with explicit ascending order"""
        processor = SortProcessor(ModelTest)
        stmt = select(ModelTest)
        sorted_stmt = processor.apply_sorting_to_statement(stmt, "name", "asc")

        assert isinstance(sorted_stmt, Select)

    def test_apply_sorting_explicit_desc(self):
        """Test sorting with explicit descending order"""
        processor = SortProcessor(ModelTest)
        stmt = select(ModelTest)
        sorted_stmt = processor.apply_sorting_to_statement(stmt, "name", "desc")

        assert isinstance(sorted_stmt, Select)

    def test_apply_sorting_mixed_orders(self):
        """Test sorting with mixed sort orders"""
        processor = SortProcessor(ModelTest)
        stmt = select(ModelTest)
        sorted_stmt = processor.apply_sorting_to_statement(
            stmt, ["name", "id", "tier_id"], ["asc", "desc", "asc"]
        )

        assert isinstance(sorted_stmt, Select)

    def test_apply_sorting_length_mismatch_error(self):
        """Test error when sort_columns and sort_orders length mismatch"""
        processor = SortProcessor(ModelTest)
        stmt = select(ModelTest)

        with pytest.raises(
            ValueError,
            match="Length of sort_columns .* must match length of sort_orders",
        ):
            processor.apply_sorting_to_statement(stmt, ["name", "id"], ["asc"])

    def test_apply_sorting_invalid_order_error(self):
        """Test error with invalid sort order"""
        processor = SortProcessor(ModelTest)
        stmt = select(ModelTest)

        with pytest.raises(ValueError, match="Invalid sort order: invalid"):
            processor.apply_sorting_to_statement(stmt, "name", "invalid")

    def test_apply_sorting_invalid_column_error(self):
        """Test error with invalid column name"""
        processor = SortProcessor(ModelTest)
        stmt = select(ModelTest)

        with pytest.raises(ArgumentError, match="Invalid sort column 'nonexistent'"):
            processor.apply_sorting_to_statement(stmt, "nonexistent")

    def test_apply_sorting_case_insensitive_orders(self):
        """Test that sort orders are case insensitive"""
        processor = SortProcessor(ModelTest)
        stmt = select(ModelTest)

        # Should work with uppercase
        sorted_stmt = processor.apply_sorting_to_statement(stmt, "name", "ASC")
        assert isinstance(sorted_stmt, Select)

        sorted_stmt = processor.apply_sorting_to_statement(stmt, "name", "DESC")
        assert isinstance(sorted_stmt, Select)

        # Should work with mixed case
        sorted_stmt = processor.apply_sorting_to_statement(stmt, "name", "Asc")
        assert isinstance(sorted_stmt, Select)


class TestJoinBuilder:
    """Test cases for JoinBuilder functionality."""

    def test_init(self):
        """Test JoinBuilder initialization"""
        builder = JoinBuilder(ModelTest)
        assert builder.model == ModelTest

    def test_prepare_joins_empty_config(self):
        """Test that prepare_joins handles empty config"""
        builder = JoinBuilder(ModelTest)
        stmt = select(ModelTest)

        # Empty joins config should return original statement
        result_stmt = builder.prepare_joins(stmt, [])
        assert result_stmt == stmt

    def test_prepare_joins_basic_functionality(self):
        """Test basic join preparation with mock config"""
        builder = JoinBuilder(ModelTest)
        stmt = select(ModelTest)

        # Create a simple mock join config
        class MockJoinConfig:
            def __init__(self):
                self.model = TierModel
                self.join_on = ModelTest.tier_id == TierModel.id
                self.join_type = "left"
                self.filters = None
                self.schema_to_select = None

        mock_join = MockJoinConfig()
        result_stmt = builder.prepare_joins(stmt, [mock_join])

        # Should return a modified statement (not the same object)
        assert result_stmt != stmt
        assert isinstance(result_stmt, Select)

    def test_prepare_joins_invalid_join_type(self):
        """Test error handling for invalid join types"""
        builder = JoinBuilder(ModelTest)
        stmt = select(ModelTest)

        class MockJoinConfig:
            def __init__(self):
                self.model = TierModel
                self.join_on = ModelTest.tier_id == TierModel.id
                self.join_type = "invalid"
                self.filters = None

        mock_join = MockJoinConfig()

        with pytest.raises(ValueError, match="Unsupported join type: invalid"):
            builder.prepare_joins(stmt, [mock_join])
