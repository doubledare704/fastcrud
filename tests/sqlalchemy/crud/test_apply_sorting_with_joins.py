import pytest
from sqlalchemy import select
from sqlalchemy.exc import ArgumentError
from fastcrud.crud.fast_crud import FastCRUD, JoinConfig
from ..conftest import (
    ModelTest,
    TierModel,
    CategoryModel,
    Author,
    Article,
)


@pytest.mark.asyncio
async def test_apply_sorting_with_joined_table(async_session, test_data, test_data_tier):
    """Test sorting on columns from a joined table."""
    # Add test data
    for tier_item in test_data_tier:
        async_session.add(TierModel(**tier_item))
    await async_session.commit()

    for user_item in test_data:
        async_session.add(ModelTest(**user_item))
    await async_session.commit()

    # Create a FastCRUD instance and a select statement
    crud = FastCRUD(ModelTest)
    stmt = select(ModelTest, TierModel.name.label("tier_name")).join(
        TierModel, ModelTest.tier_id == TierModel.id
    )

    # Create a JoinConfig for the joined table
    joins_config = [
        JoinConfig(
            model=TierModel,
            join_on=ModelTest.tier_id == TierModel.id,
            join_prefix="tier_",
        )
    ]

    # Apply sorting on a column from the joined table
    sorted_stmt = crud._apply_sorting(stmt, "tier_name", "asc", joins_config)

    # Execute the statement and get the results
    result = await async_session.execute(sorted_stmt)
    sorted_data = result.all()

    # Verify that the results are sorted by tier_name
    for i in range(len(sorted_data) - 1):
        current_tier_name = sorted_data[i][1]  # tier_name is at index 1
        next_tier_name = sorted_data[i + 1][1]
        assert current_tier_name <= next_tier_name


@pytest.mark.asyncio
async def test_apply_sorting_with_joined_table_and_prefix(async_session, test_data, test_data_tier):
    """Test sorting on columns from a joined table with a prefix."""
    # Add test data
    for tier_item in test_data_tier:
        async_session.add(TierModel(**tier_item))
    await async_session.commit()

    for user_item in test_data:
        async_session.add(ModelTest(**user_item))
    await async_session.commit()

    # Create a FastCRUD instance and a select statement
    crud = FastCRUD(ModelTest)
    stmt = select(ModelTest, TierModel.name.label("tier_name")).join(
        TierModel, ModelTest.tier_id == TierModel.id
    )

    # Create a JoinConfig for the joined table with a prefix
    joins_config = [
        JoinConfig(
            model=TierModel,
            join_on=ModelTest.tier_id == TierModel.id,
            join_prefix="tier_",
        )
    ]

    # Apply sorting on a column from the joined table with the prefix
    sorted_stmt = crud._apply_sorting(stmt, "tier_name", "asc", joins_config)

    # Execute the statement and get the results
    result = await async_session.execute(sorted_stmt)
    sorted_data = result.all()

    # Verify that the results are sorted by tier_name
    for i in range(len(sorted_data) - 1):
        current_tier_name = sorted_data[i][1]  # tier_name is at index 1
        next_tier_name = sorted_data[i + 1][1]
        assert current_tier_name <= next_tier_name


@pytest.mark.asyncio
async def test_apply_sorting_with_multiple_joined_tables(async_session, test_data, test_data_tier, test_data_category):
    """Test sorting on columns from multiple joined tables."""
    # Add test data
    for tier_item in test_data_tier:
        async_session.add(TierModel(**tier_item))
    await async_session.commit()

    for category_item in test_data_category:
        async_session.add(CategoryModel(**category_item))
    await async_session.commit()

    for user_item in test_data:
        async_session.add(ModelTest(**user_item))
    await async_session.commit()

    # Create a FastCRUD instance and a select statement
    crud = FastCRUD(ModelTest)
    stmt = select(
        ModelTest,
        TierModel.name.label("tier_name"),
        CategoryModel.name.label("category_name")
    ).join(
        TierModel, ModelTest.tier_id == TierModel.id
    ).join(
        CategoryModel, ModelTest.category_id == CategoryModel.id
    )

    # Create JoinConfig objects for the joined tables
    joins_config = [
        JoinConfig(
            model=TierModel,
            join_on=ModelTest.tier_id == TierModel.id,
            join_prefix="tier_",
        ),
        JoinConfig(
            model=CategoryModel,
            join_on=ModelTest.category_id == CategoryModel.id,
            join_prefix="category_",
        )
    ]

    # Apply sorting on columns from both joined tables
    sorted_stmt = crud._apply_sorting(
        stmt, ["tier_name", "category_name"], ["asc", "desc"], joins_config
    )

    # Execute the statement and get the results
    result = await async_session.execute(sorted_stmt)
    sorted_data = result.all()

    # Verify that the results are sorted by tier_name (asc) and then by category_name (desc)
    for i in range(len(sorted_data) - 1):
        current_tier_name = sorted_data[i][1]  # tier_name is at index 1
        next_tier_name = sorted_data[i + 1][1]
        
        if current_tier_name == next_tier_name:
            current_category_name = sorted_data[i][2]  # category_name is at index 2
            next_category_name = sorted_data[i + 1][2]
            assert current_category_name >= next_category_name  # desc order
        else:
            assert current_tier_name <= next_tier_name  # asc order


@pytest.mark.asyncio
async def test_apply_sorting_with_invalid_joined_column(async_session, test_data, test_data_tier):
    """Test sorting on an invalid column from a joined table."""
    # Add test data
    for tier_item in test_data_tier:
        async_session.add(TierModel(**tier_item))
    await async_session.commit()

    for user_item in test_data:
        async_session.add(ModelTest(**user_item))
    await async_session.commit()

    # Create a FastCRUD instance and a select statement
    crud = FastCRUD(ModelTest)
    stmt = select(ModelTest).join(
        TierModel, ModelTest.tier_id == TierModel.id
    )

    # Create a JoinConfig for the joined table
    joins_config = [
        JoinConfig(
            model=TierModel,
            join_on=ModelTest.tier_id == TierModel.id,
            join_prefix="tier_",
        )
    ]

    # Apply sorting on an invalid column from the joined table
    with pytest.raises(ArgumentError):
        crud._apply_sorting(stmt, "tier_invalid_column", "asc", joins_config)


@pytest.mark.asyncio
async def test_apply_sorting_with_one_to_many_relationship(async_session):
    """Test sorting on columns from a one-to-many relationship."""
    # Create test data
    author1 = Author(id=1, name="Author 1")
    author2 = Author(id=2, name="Author 2")

    # Create articles with different titles and dates for sorting
    article1 = Article(id=1, title="C Article", content="Content 1", author_id=1, published_date="2023-01-01")
    article2 = Article(id=2, title="A Article", content="Content 2", author_id=1, published_date="2023-03-01")
    article3 = Article(id=3, title="B Article", content="Content 3", author_id=1, published_date="2023-02-01")
    article4 = Article(id=4, title="D Article", content="Content 4", author_id=2, published_date="2023-01-15")

    async_session.add_all([author1, author2, article1, article2, article3, article4])
    await async_session.commit()

    # Create a FastCRUD instance and a select statement
    crud = FastCRUD(Author)
    stmt = select(Author, Article).join(
        Article, Author.id == Article.author_id
    )

    # Create a JoinConfig for the joined table
    joins_config = [
        JoinConfig(
            model=Article,
            join_on=Author.id == Article.author_id,
            join_prefix="article_",
            relationship_type="one-to-many",
        )
    ]

    # Apply sorting on a column from the joined table
    sorted_stmt = crud._apply_sorting(stmt, "article_title", "asc", joins_config)

    # Execute the statement and get the results
    result = await async_session.execute(sorted_stmt)
    sorted_data = result.all()

    # Verify that the results are sorted by article_title
    for i in range(len(sorted_data) - 1):
        if sorted_data[i][0].id == sorted_data[i + 1][0].id:  # Same author
            current_title = sorted_data[i][1].title
            next_title = sorted_data[i + 1][1].title
            assert current_title <= next_title