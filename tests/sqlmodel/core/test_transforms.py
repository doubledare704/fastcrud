"""Test data transformation functions."""

import pytest
from fastcrud.core.data.transforms import sort_nested_list


class TestSortNestedList:
    """Test sort_nested_list function."""

    def test_empty_list(self):
        """Test sorting empty list returns empty list."""
        result = sort_nested_list([], ["id"])
        assert result == []

    def test_no_sort_columns(self):
        """Test no sort columns returns original list."""
        data = [{"id": 1}, {"id": 2}]
        result = sort_nested_list(data, [])
        assert result == data

    def test_invalid_sort_orders_length_mismatch(self):
        """Test mismatched sort_columns and sort_orders raises error."""
        data = [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]
        with pytest.raises(
            ValueError, match="The length of sort_columns and sort_orders must match"
        ):
            sort_nested_list(data, ["id", "name"], ["asc"])

    def test_invalid_sort_order_value(self):
        """Test invalid sort order value raises error."""
        data = [{"id": 1}, {"id": 2}]
        with pytest.raises(
            ValueError, match="Invalid sort order.*Only 'asc' or 'desc' are allowed"
        ):
            sort_nested_list(data, ["id"], ["invalid"])

    def test_single_sort_column_as_string(self):
        """Test single sort column passed as string."""
        data = [{"id": 2}, {"id": 1}]
        result = sort_nested_list(data, "id", "asc")
        assert result == [{"id": 1}, {"id": 2}]

    def test_single_sort_order_expanded_to_all_columns(self):
        """Test single sort order applied to all columns."""
        data = [{"id": 2, "name": "B"}, {"id": 1, "name": "A"}]
        result = sort_nested_list(data, ["name", "id"], "desc")
        assert result == [{"id": 2, "name": "B"}, {"id": 1, "name": "A"}]

    def test_descending_sort(self):
        """Test descending sort order."""
        data = [{"id": 1}, {"id": 3}, {"id": 2}]
        result = sort_nested_list(data, ["id"], ["desc"])
        assert result == [{"id": 3}, {"id": 2}, {"id": 1}]
