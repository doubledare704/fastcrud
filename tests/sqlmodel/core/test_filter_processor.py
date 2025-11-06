"""
Tests for the FilterProcessor engine with SQLModel models.

This module tests the core filtering functionality including all operators,
OR/NOT conditions, multi-field OR, and error handling.
"""

import pytest
from sqlalchemy.sql.elements import ColumnElement

from fastcrud.core.filtering import FilterProcessor
from tests.sqlmodel.conftest import ModelTest, TierModel


class TestFilterProcessor:
    """Test cases for FilterProcessor functionality with SQLModel models."""

    def test_simple_equality_filter(self):
        """Test simple equality filters: field=value"""
        processor = FilterProcessor(ModelTest)
        filters = processor.parse_filters(name="Alice")

        assert len(filters) == 1
        assert isinstance(filters[0], ColumnElement)

    def test_comparison_operators(self):
        """Test all comparison operators (gt, lt, gte, lte, ne)"""
        processor = FilterProcessor(ModelTest)

        # Test greater than
        filters = processor.parse_filters(id__gt=5)
        assert len(filters) == 1

        # Test less than
        filters = processor.parse_filters(id__lt=10)
        assert len(filters) == 1

        # Test greater than or equal
        filters = processor.parse_filters(id__gte=1)
        assert len(filters) == 1

        # Test less than or equal
        filters = processor.parse_filters(id__lte=100)
        assert len(filters) == 1

        # Test not equal
        filters = processor.parse_filters(id__ne=0)
        assert len(filters) == 1

    def test_string_operators(self):
        """Test string-specific operators (like, ilike, startswith, endswith, contains)"""
        processor = FilterProcessor(ModelTest)

        # Test LIKE
        filters = processor.parse_filters(name__like="%Alice%")
        assert len(filters) == 1

        # Test case-insensitive LIKE
        filters = processor.parse_filters(name__ilike="%alice%")
        assert len(filters) == 1

        # Test startswith
        filters = processor.parse_filters(name__startswith="A")
        assert len(filters) == 1

        # Test endswith
        filters = processor.parse_filters(name__endswith="e")
        assert len(filters) == 1

        # Test contains
        filters = processor.parse_filters(name__contains="lic")
        assert len(filters) == 1

    def test_is_operators(self):
        """Test IS and IS NOT operators"""
        processor = FilterProcessor(ModelTest)

        # Test IS NULL
        filters = processor.parse_filters(category_id__is=None)
        assert len(filters) == 1

        # Test IS NOT NULL
        filters = processor.parse_filters(category_id__is_not=None)
        assert len(filters) == 1

    def test_in_operator(self):
        """Test IN and NOT IN operators"""
        processor = FilterProcessor(ModelTest)

        # Test IN with list
        filters = processor.parse_filters(id__in=[1, 2, 3])
        assert len(filters) == 1

        # Test IN with tuple
        filters = processor.parse_filters(id__in=(1, 2, 3))
        assert len(filters) == 1

        # Test NOT IN
        filters = processor.parse_filters(id__not_in=[4, 5, 6])
        assert len(filters) == 1

    def test_between_operator(self):
        """Test BETWEEN operator"""
        processor = FilterProcessor(ModelTest)

        filters = processor.parse_filters(id__between=[1, 10])
        assert len(filters) == 1

    def test_or_filter_single_field(self):
        """Test OR conditions on a single field"""
        processor = FilterProcessor(ModelTest)

        # Test OR with multiple operators on same field
        filters = processor.parse_filters(id__or={"gt": 5, "lt": 100})
        assert len(filters) == 1

        # Test OR with list values
        filters = processor.parse_filters(name__or={"eq": ["Alice", "Bob"]})
        assert len(filters) == 1

    def test_not_filter_single_field(self):
        """Test NOT conditions on a single field"""
        processor = FilterProcessor(ModelTest)

        # Test NOT with multiple conditions
        filters = processor.parse_filters(id__not={"lt": 5, "gt": 100})
        assert len(filters) == 1

    def test_multi_field_or_filter(self):
        """Test multi-field OR filters: _or={'field1': value1, 'field2': value2}"""
        processor = FilterProcessor(ModelTest)

        filters = processor.parse_filters(_or={"name": "Alice", "id": 1})
        assert len(filters) == 1

    def test_multiple_filters_combined(self):
        """Test combining multiple different filter types"""
        processor = FilterProcessor(ModelTest)

        filters = processor.parse_filters(
            name="Alice",  # Simple equality
            id__gt=5,  # Greater than
            tier_id__in=[1, 2],  # IN operator
            _or={"name": "Bob", "id": 10},  # Multi-field OR
        )
        assert len(filters) == 4

    def test_invalid_operator_error(self):
        """Test error handling for invalid operators"""
        processor = FilterProcessor(ModelTest)

        with pytest.raises(ValueError, match="Unsupported filter operator"):
            processor.parse_filters(id__invalid_op=5)

    def test_invalid_field_error(self):
        """Test error handling for invalid field names"""
        processor = FilterProcessor(ModelTest)

        with pytest.raises(ValueError, match="Invalid column"):
            processor.parse_filters(nonexistent_field=5)

    def test_in_operator_validation_error(self):
        """Test validation error for IN operator with invalid value type"""
        processor = FilterProcessor(ModelTest)

        with pytest.raises(ValueError, match="filter must be tuple, list or set"):
            processor.parse_filters(id__in="invalid")

    def test_between_operator_validation_error(self):
        """Test validation error for BETWEEN operator with wrong number of values"""
        processor = FilterProcessor(ModelTest)

        with pytest.raises(
            ValueError, match="Between operator requires exactly 2 values"
        ):
            processor.parse_filters(id__between=[1])

        with pytest.raises(ValueError, match="filter must be tuple, list or set"):
            processor.parse_filters(id__between="invalid")

    def test_or_filter_validation_error(self):
        """Test validation error for OR filter with invalid value type"""
        processor = FilterProcessor(ModelTest)

        with pytest.raises(ValueError, match="OR filter value must be a dictionary"):
            processor.parse_filters(id__or="invalid")

    def test_not_filter_validation_error(self):
        """Test validation error for NOT filter with invalid value type"""
        processor = FilterProcessor(ModelTest)

        with pytest.raises(ValueError, match="NOT filter value must be a dictionary"):
            processor.parse_filters(id__not="invalid")

    def test_multi_field_or_validation_error(self):
        """Test validation error for multi-field OR with invalid value type"""
        processor = FilterProcessor(ModelTest)

        with pytest.raises(
            ValueError, match="Multi-field OR filter must be a dictionary"
        ):
            processor.parse_filters(_or="invalid")

    def test_joined_filter_simple_equality(self):
        """Test joined filters with simple equality"""
        processor = FilterProcessor(ModelTest)

        # Test simple joined filter without operator
        filters = processor.parse_filters(**{"tier.name": "Premium"})
        assert len(filters) == 1

    def test_joined_filter_with_operator(self):
        """Test joined filters with explicit operator"""
        processor = FilterProcessor(ModelTest)

        # Test joined filter with operator
        filters = processor.parse_filters(**{"tier.name__eq": "Premium"})
        assert len(filters) == 1

        # Test with other operators
        filters = processor.parse_filters(**{"tier.id__gt": 1})
        assert len(filters) == 1

    def test_joined_filter_invalid_relationship(self):
        """Test error handling for invalid relationships"""
        processor = FilterProcessor(ModelTest)

        with pytest.raises(ValueError, match="Relationship 'nonexistent' not found"):
            processor.parse_filters(**{"nonexistent.name": "value"})

    def test_joined_filter_invalid_field(self):
        """Test error handling for invalid fields in joined models"""
        processor = FilterProcessor(ModelTest)

        with pytest.raises(ValueError, match="Column 'nonexistent' not found"):
            processor.parse_filters(**{"tier.nonexistent": "value"})

    def test_model_override(self):
        """Test using different model in parse_filters call"""
        processor = FilterProcessor(ModelTest)

        # Use TierModel instead of ModelTest
        filters = processor.parse_filters(model=TierModel, name="Premium")
        assert len(filters) == 1

    def test_empty_filters(self):
        """Test parsing with no filter arguments"""
        processor = FilterProcessor(ModelTest)

        filters = processor.parse_filters()
        assert len(filters) == 0

    def test_multi_field_or_invalid_field_error(self):
        """Test that multi-field OR raises error for invalid fields"""
        processor = FilterProcessor(ModelTest)

        # Should raise error for invalid field in multi-field OR
        with pytest.raises(ValueError, match="Invalid column 'invalid_field'"):
            processor.parse_filters(_or={"name": "Alice", "invalid_field": "value"})
