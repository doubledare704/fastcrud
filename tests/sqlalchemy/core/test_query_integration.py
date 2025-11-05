"""
Integration tests for Query Builder + Filter Processor.

This module tests how the filtering and query building engines work together
to create complete SQL queries.
"""

from sqlalchemy import Select

from fastcrud.core.filtering import FilterProcessor
from fastcrud.core.query import SQLQueryBuilder
from tests.sqlalchemy.conftest import ModelTest


class TestQueryIntegration:
    """Test integration between FilterProcessor and SQLQueryBuilder."""

    def test_filter_and_query_integration(self):
        """Test complete integration of filtering and query building"""
        # Initialize both processors
        filter_processor = FilterProcessor(ModelTest)
        query_builder = SQLQueryBuilder(ModelTest)

        # Parse filters
        filters = filter_processor.parse_filters(
            name="Alice", id__gt=5, tier_id__in=[1, 2]
        )

        # Build query step by step
        stmt = query_builder.build_base_select()
        stmt = query_builder.apply_filters(stmt, filters)
        stmt = query_builder.apply_sorting(stmt, ["name", "id"], ["asc", "desc"])
        stmt = query_builder.apply_pagination(stmt, offset=10, limit=20)

        assert isinstance(stmt, Select)
        assert len(filters) == 3
        assert stmt._offset_clause.value == 10
        assert stmt._limit_clause.value == 20

    def test_complex_filter_query_chain(self):
        """Test complex filter scenarios with query building"""
        filter_processor = FilterProcessor(ModelTest)
        query_builder = SQLQueryBuilder(ModelTest)

        # Complex filters with OR and NOT conditions
        filters = filter_processor.parse_filters(
            id__or={"gt": 10, "lt": 100},
            name__not={"like": "%test%"},
            _or={"tier_id": 1, "category_id": 2},
        )

        # Build query
        stmt = query_builder.build_base_select([ModelTest.id, ModelTest.name])
        stmt = query_builder.apply_filters(stmt, filters)
        stmt = query_builder.apply_sorting(stmt, "name")

        assert isinstance(stmt, Select)
        assert len(filters) == 3
        assert len(stmt.selected_columns) == 2

    def test_empty_filters_with_query_building(self):
        """Test query building with no filters"""
        filter_processor = FilterProcessor(ModelTest)
        query_builder = SQLQueryBuilder(ModelTest)

        # No filters
        filters = filter_processor.parse_filters()

        # Build basic query
        stmt = query_builder.build_base_select()
        stmt = query_builder.apply_filters(stmt, filters)
        stmt = query_builder.apply_pagination(stmt, limit=50)

        assert isinstance(stmt, Select)
        assert len(filters) == 0
        assert stmt._limit_clause.value == 50
