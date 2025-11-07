"""Test validation functions."""

import pytest
from fastcrud.core.filtering.validators import (
    validate_joined_filter_format,
    validate_filter_operator,
)


class TestJoinedFilterValidation:
    """Test joined filter format validation."""

    def test_valid_filter_keys(self):
        """Test valid filter key formats."""
        # These should not raise exceptions
        validate_joined_filter_format("user.name")
        validate_joined_filter_format("user.company.name__eq")
        validate_joined_filter_format("model.field__gt")

    def test_invalid_empty_filter_key(self):
        """Test empty filter key raises error."""
        with pytest.raises(ValueError, match="Filter key must be a non-empty string"):
            validate_joined_filter_format("")

    def test_invalid_non_string_filter_key(self):
        """Test non-string filter key raises error."""
        with pytest.raises(ValueError, match="Filter key must be a non-empty string"):
            validate_joined_filter_format(None)

    def test_invalid_leading_dot(self):
        """Test filter key starting with dot raises error."""
        with pytest.raises(ValueError, match="Invalid filter key format"):
            validate_joined_filter_format(".user.name")

    def test_invalid_trailing_dot(self):
        """Test filter key ending with dot raises error."""
        with pytest.raises(ValueError, match="Invalid filter key format"):
            validate_joined_filter_format("user.name.")

    def test_invalid_consecutive_dots(self):
        """Test filter key with consecutive dots raises error."""
        with pytest.raises(
            ValueError, match="Invalid filter key format \\(consecutive dots\\)"
        ):
            validate_joined_filter_format("user..name")


class TestOperatorValidation:
    """Test filter operator validation."""

    def test_valid_operators(self):
        """Test valid operator and value combinations."""
        # These should not raise exceptions
        validate_filter_operator("eq", "test")
        validate_filter_operator("in", [1, 2, 3])
        validate_filter_operator("between", [1, 10])
        validate_filter_operator("not_in", {1, 2, 3})

    def test_invalid_in_operator_value(self):
        """Test 'in' operator with invalid value type."""
        with pytest.raises(ValueError, match="requires a list, tuple, or set value"):
            validate_filter_operator("in", "invalid")

    def test_invalid_not_in_operator_value(self):
        """Test 'not_in' operator with invalid value type."""
        with pytest.raises(ValueError, match="requires a list, tuple, or set value"):
            validate_filter_operator("not_in", "invalid")

    def test_invalid_between_operator_value(self):
        """Test 'between' operator with invalid value type."""
        with pytest.raises(ValueError, match="requires a list, tuple, or set value"):
            validate_filter_operator("between", "invalid")

    def test_invalid_between_length(self):
        """Test 'between' operator with wrong number of values."""
        with pytest.raises(
            ValueError, match="Between operator requires exactly 2 values"
        ):
            validate_filter_operator("between", [1])

        with pytest.raises(
            ValueError, match="Between operator requires exactly 2 values"
        ):
            validate_filter_operator("between", [1, 2, 3])
