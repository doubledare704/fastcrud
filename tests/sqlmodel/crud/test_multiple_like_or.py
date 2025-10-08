import pytest
from fastcrud import FastCRUD


@pytest.mark.asyncio
async def test_or_filter_with_multiple_like_values_sqlmodel(async_session, test_model):
    """Test OR filter with multiple values for the same operator (like) - SQLModel version"""
    # Create test data
    test_data = [
        {"name": "Alice Johnson", "tier_id": 1, "category_id": 1},
        {"name": "Bob Smith", "tier_id": 2, "category_id": 1},
        {"name": "Charlie Brown", "tier_id": 3, "category_id": 2},
        {"name": "Frank Miller", "tier_id": 4, "category_id": 2},
        {"name": "Alice Cooper", "tier_id": 5, "category_id": 1},
        {"name": "Frank Sinatra", "tier_id": 6, "category_id": 2},
    ]

    for item in test_data:
        async_session.add(test_model(**item))
    await async_session.commit()

    crud = FastCRUD(test_model)

    # Test with multiple like patterns using list syntax
    result = await crud.get_multi(
        async_session, name__or={"like": ["Alice%", "Frank%"]}
    )

    assert (
        len(result["data"]) == 4
    )  # Alice Johnson, Alice Cooper, Frank Miller, Frank Sinatra
    names = [item["name"] for item in result["data"]]
    assert all(name.startswith("Alice") or name.startswith("Frank") for name in names)

    # Test with case-insensitive multiple patterns
    result = await crud.get_multi(
        async_session, name__or={"ilike": ["%cooper", "%sinatra"]}
    )

    assert len(result["data"]) == 2
    names = [item["name"] for item in result["data"]]
    assert "Alice Cooper" in names
    assert "Frank Sinatra" in names


@pytest.mark.asyncio
async def test_not_filter_with_multiple_like_values_sqlmodel(async_session, test_model):
    """Test NOT filter with multiple values for the same operator - SQLModel version"""
    test_data = [
        {"name": "Alice Johnson", "tier_id": 1, "category_id": 1},
        {"name": "Bob Smith", "tier_id": 2, "category_id": 1},
        {"name": "Charlie Brown", "tier_id": 3, "category_id": 2},
        {"name": "David Jones", "tier_id": 4, "category_id": 2},
    ]

    for item in test_data:
        async_session.add(test_model(**item))
    await async_session.commit()

    crud = FastCRUD(test_model)

    # Test NOT filter with multiple like patterns
    result = await crud.get_multi(async_session, name__not={"like": ["Alice%", "Bob%"]})

    assert len(result["data"]) == 2
    names = [item["name"] for item in result["data"]]
    assert "Charlie Brown" in names
    assert "David Jones" in names
    assert "Alice Johnson" not in names
    assert "Bob Smith" not in names


@pytest.mark.asyncio
async def test_combined_filters_with_list_or_sqlmodel(async_session, test_model):
    """Test combining regular filters with list-based OR filters - SQLModel version"""
    test_data = [
        {"name": "Alice Johnson", "tier_id": 1, "category_id": 1},
        {"name": "Alice Cooper", "tier_id": 2, "category_id": 2},
        {"name": "Bob Smith", "tier_id": 3, "category_id": 1},
        {"name": "Frank Miller", "tier_id": 4, "category_id": 1},
        {"name": "Frank Sinatra", "tier_id": 5, "category_id": 2},
    ]

    for item in test_data:
        async_session.add(test_model(**item))
    await async_session.commit()

    crud = FastCRUD(test_model)

    # Combine regular filter with list-based OR filter
    result = await crud.get_multi(
        async_session,
        category_id=1,  # AND condition
        name__or={"like": ["Alice%", "Frank%"]},  # OR condition with list
    )

    assert len(result["data"]) == 2
    for item in result["data"]:
        assert item["category_id"] == 1
        assert item["name"].startswith("Alice") or item["name"].startswith("Frank")

    names = [item["name"] for item in result["data"]]
    assert "Alice Johnson" in names
    assert "Frank Miller" in names
    assert "Alice Cooper" not in names  # category_id=2
    assert "Frank Sinatra" not in names  # category_id=2
