"""
Test for composite primary key deduplication bug
https://github.com/benavlabs/fastcrud/issues/XXX

The bug: _get_primary_key only returns the first primary key for composite keys,
causing incorrect deduplication in one-to-many relationships.
"""

import pytest
from fastcrud import FastCRUD, JoinConfig
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from ...sqlalchemy.conftest import Base


# Test models that reproduce the composite PK deduplication bug
class ParentModel(Base):
    __tablename__ = "parent_dedup_test"
    id = Column(Integer, primary_key=True)
    name = Column(String(50))
    children = relationship("ChildModel", back_populates="parent", lazy="select")


class ChildModel(Base):
    __tablename__ = "child_dedup_test"
    # Composite primary key that triggers the bug
    child_id = Column(Integer, primary_key=True)  # First PK - used for deduplication
    version = Column(Integer, primary_key=True)  # Second PK - ignored by deduplication
    name = Column(String(50))
    parent_id = Column(Integer, ForeignKey("parent_dedup_test.id"))
    parent = relationship("ParentModel", back_populates="children")


# Alternative scenario: same product in same warehouse but different batches
class WarehouseModel(Base):
    __tablename__ = "warehouse_dedup_test"
    id = Column(Integer, primary_key=True)
    name = Column(String(50))
    inventory = relationship(
        "InventoryModel", back_populates="warehouse", lazy="select"
    )


class InventoryModel(Base):
    __tablename__ = "inventory_dedup_test"
    # Composite PK: same product can exist in multiple batches
    product_id = Column(
        Integer, primary_key=True
    )  # First PK - causes deduplication issue
    batch_id = Column(Integer, primary_key=True)  # Second PK - ignored
    quantity = Column(Integer)
    warehouse_id = Column(Integer, ForeignKey("warehouse_dedup_test.id"))
    warehouse = relationship("WarehouseModel", back_populates="inventory")


# Pydantic schemas
class ChildRead(BaseModel):
    child_id: int
    version: int
    name: str


class ParentRead(BaseModel):
    id: int
    name: str
    children: list[ChildRead] = []


class InventoryRead(BaseModel):
    product_id: int
    batch_id: int
    quantity: int


class WarehouseRead(BaseModel):
    id: int
    name: str
    inventory: list[InventoryRead] = []


@pytest.mark.asyncio
async def test_composite_pk_deduplication_bug_scenario_1(async_session):
    """
    Test scenario 1: Children with same child_id but different versions

    This test creates a parent with children that have:
    - Child 1: (child_id=1, version=1)
    - Child 2: (child_id=1, version=2)  <- Different version, should be separate record

    Due to the bug, only Child 1 will be returned because deduplication
    only looks at child_id (first primary key) and considers them duplicates.
    """
    # Create test data that triggers the deduplication bug
    parent = ParentModel(id=1, name="Parent A")

    # Critical: Both children have same child_id (first PK) but different version (second PK)
    child1 = ChildModel(child_id=1, version=1, name="Child 1-v1", parent_id=1)
    child2 = ChildModel(child_id=1, version=2, name="Child 1-v2", parent_id=1)

    async_session.add_all([parent, child1, child2])
    await async_session.commit()

    # Configure FastCRUD join
    join_config = [
        JoinConfig(
            model=ChildModel,
            join_on=ParentModel.id == ChildModel.parent_id,
            join_prefix="children_",
            join_type="left",
            schema_to_select=ChildRead,
            relationship_type="one-to-many",
        )
    ]

    crud_parent = FastCRUD(ParentModel)

    # Execute the problematic query
    result = await crud_parent.get_multi_joined(
        db=async_session,
        schema_to_select=ParentRead,
        offset=0,
        limit=10,
        nest_joins=True,
        joins_config=join_config,
        return_as_model=False,
    )

    # Verify the bug: should get 2 children but only gets 1
    assert result is not None
    assert "data" in result
    data = result["data"]
    assert len(data) == 1

    parent_data = data[0]
    children = parent_data.get("children", [])

    # This assertion will FAIL due to the bug - we expect 2 but get 1
    assert (
        len(children) == 2
    ), f"Expected 2 children but got {len(children)}. Children: {children}"

    # Verify we have both versions
    child_versions = {child["version"] for child in children}
    assert child_versions == {1, 2}, f"Expected versions 1 and 2, got {child_versions}"


@pytest.mark.asyncio
async def test_composite_pk_deduplication_bug_scenario_2(async_session):
    """
    Test scenario 2: Inventory with same product_id but different batches

    This test creates a warehouse with inventory items that have:
    - Item 1: (product_id=100, batch_id=1)
    - Item 2: (product_id=100, batch_id=2)  <- Same product, different batch

    Due to the bug, only Item 1 will be returned because deduplication
    only looks at product_id (first primary key).
    """
    # Create test data
    warehouse = WarehouseModel(id=1, name="Main Warehouse")

    # Critical: Both items have same product_id but different batch_id
    item1 = InventoryModel(product_id=100, batch_id=1, quantity=50, warehouse_id=1)
    item2 = InventoryModel(product_id=100, batch_id=2, quantity=30, warehouse_id=1)

    async_session.add_all([warehouse, item1, item2])
    await async_session.commit()

    # Configure FastCRUD join
    join_config = [
        JoinConfig(
            model=InventoryModel,
            join_on=WarehouseModel.id == InventoryModel.warehouse_id,
            join_prefix="inventory_",
            join_type="left",
            schema_to_select=InventoryRead,
            relationship_type="one-to-many",
        )
    ]

    crud_warehouse = FastCRUD(WarehouseModel)

    # Execute the problematic query
    result = await crud_warehouse.get_multi_joined(
        db=async_session,
        schema_to_select=WarehouseRead,
        offset=0,
        limit=10,
        nest_joins=True,
        joins_config=join_config,
        return_as_model=False,
    )

    # Verify the bug
    assert result is not None
    assert "data" in result
    data = result["data"]
    assert len(data) == 1

    warehouse_data = data[0]
    inventory = warehouse_data.get("inventory", [])

    # This assertion will FAIL due to the bug - we expect 2 but get 1
    assert (
        len(inventory) == 2
    ), f"Expected 2 inventory items but got {len(inventory)}. Items: {inventory}"

    # Verify we have both batches
    batch_ids = {item["batch_id"] for item in inventory}
    assert batch_ids == {1, 2}, f"Expected batch IDs 1 and 2, got {batch_ids}"


@pytest.mark.asyncio
async def test_get_primary_key_function_behavior():
    """
    Test to verify the root cause: _get_primary_key only returns first primary key
    """
    from fastcrud.core import get_first_primary_key, get_primary_key_columns

    # Test with ChildModel (composite PK: child_id, version)
    all_pks = get_primary_key_columns(ChildModel)
    first_pk = get_first_primary_key(ChildModel)

    # Verify the bug: should return all PKs but only returns first
    pk_names = [pk.name for pk in all_pks]
    assert (
        len(pk_names) == 2
    ), f"Expected 2 primary keys, got {len(pk_names)}: {pk_names}"
    assert "child_id" in pk_names and "version" in pk_names

    # This shows the bug: only first PK is returned
    assert first_pk == "child_id", f"Expected 'child_id' as first PK, got '{first_pk}'"

    # The bug: _get_primary_key should return a composite key representation,
    # not just the first key, for proper deduplication


@pytest.mark.asyncio
async def test_composite_pk_with_different_first_keys_works(async_session):
    """
    Control test: Verify that children with different first primary keys work correctly

    This should work fine because the first primary keys are different,
    so the buggy deduplication logic won't consider them duplicates.
    """
    parent = ParentModel(id=1, name="Parent A")

    # Different child_id values - this should work fine
    child1 = ChildModel(child_id=1, version=1, name="Child 1-v1", parent_id=1)
    child2 = ChildModel(child_id=2, version=1, name="Child 2-v1", parent_id=1)

    async_session.add_all([parent, child1, child2])
    await async_session.commit()

    join_config = [
        JoinConfig(
            model=ChildModel,
            join_on=ParentModel.id == ChildModel.parent_id,
            join_prefix="children_",
            join_type="left",
            schema_to_select=ChildRead,
            relationship_type="one-to-many",
        )
    ]

    crud_parent = FastCRUD(ParentModel)

    result = await crud_parent.get_multi_joined(
        db=async_session,
        schema_to_select=ParentRead,
        offset=0,
        limit=10,
        nest_joins=True,
        joins_config=join_config,
        return_as_model=False,
    )

    # This should work correctly because first PKs are different
    assert result is not None
    data = result["data"]
    assert len(data) == 1

    parent_data = data[0]
    children = parent_data.get("children", [])

    # This should pass - different first PKs work fine
    assert len(children) == 2, f"Expected 2 children but got {len(children)}"

    child_ids = {child["child_id"] for child in children}
    assert child_ids == {1, 2}, f"Expected child IDs 1 and 2, got {child_ids}"
