import pytest
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select
from fastcrud.crud.fast_crud import FastCRUD
from sqlalchemy.exc import MultipleResultsFound, NoResultFound


# Define Pydantic schemas for delete operations for testing
class ItemDeleteSchema(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    tier_id: Optional[int] = None
    is_deleted: Optional[bool] = None # For querying soft-deleted items

class TierDeleteSchema(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None


@pytest.mark.asyncio
async def test_db_delete_hard_delete(async_session, test_data_tier, tier_model):
    for tier_item in test_data_tier:
        async_session.add(tier_model(**tier_item))
    await async_session.commit()

    crud = FastCRUD(tier_model)
    some_existing_id = test_data_tier[0]["id"]
    await crud.db_delete(db=async_session, id=some_existing_id)

    deleted_record = await async_session.execute(
        select(tier_model).where(tier_model.id == some_existing_id)
    )
    assert deleted_record.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_delete_soft_delete(async_session, test_data, test_model):
    for item in test_data:
        async_session.add(test_model(**item))
    await async_session.commit()

    crud = FastCRUD(test_model)
    some_existing_id = test_data[0]["id"]
    await crud.delete(db=async_session, id=some_existing_id)

    soft_deleted_record = await async_session.execute(
        select(test_model).where(test_model.id == some_existing_id)
    )
    soft_deleted = soft_deleted_record.scalar_one()
    assert soft_deleted.is_deleted is True
    assert soft_deleted.deleted_at is not None


@pytest.mark.asyncio
async def test_delete_hard_delete_as_fallback(
    async_session, test_data_tier, tier_model
):
    for tier_item in test_data_tier:
        async_session.add(tier_model(**tier_item))
    await async_session.commit()

    crud = FastCRUD(tier_model)
    some_existing_id = test_data_tier[0]["id"]
    await crud.delete(db=async_session, id=some_existing_id)

    hard_deleted_record = await async_session.execute(
        select(tier_model).where(tier_model.id == some_existing_id)
    )
    assert hard_deleted_record.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_delete_multiple_records(async_session, test_data, test_model):
    for item in test_data:
        async_session.add(test_model(**item))
    await async_session.commit()

    crud = FastCRUD(test_model)
    with pytest.raises(Exception):
        await crud.delete(db=async_session, allow_multiple=False, tier_id=1)


@pytest.mark.asyncio
async def test_get_with_advanced_filters(async_session, test_data, test_model):
    for item in test_data:
        async_session.add(test_model(**item))
    await async_session.commit()

    crud = FastCRUD(test_model)
    records = await crud.get_multi(db=async_session, id__gt=5)
    for record in records["data"]:
        assert record["id"] > 5, "All fetched records should have 'id' greater than 5"


@pytest.mark.asyncio
async def test_soft_delete_with_custom_columns(async_session, test_data, test_model):
    crud = FastCRUD(
        test_model, is_deleted_column="is_deleted", deleted_at_column="deleted_at"
    )
    some_existing_id = test_data[0]["id"]

    for item in test_data:
        async_session.add(test_model(**item))
    await async_session.commit()

    await crud.delete(db=async_session, id=some_existing_id, allow_multiple=False)

    deleted_record = await async_session.execute(
        select(test_model)
        .where(test_model.id == some_existing_id)
        .where(getattr(test_model, "is_deleted") == True)  # noqa
    )
    deleted_record = deleted_record.scalar_one_or_none()

    assert deleted_record is not None, "Record should exist after soft delete"
    assert (
        getattr(deleted_record, "is_deleted") == True  # noqa
    ), "Record should be marked as soft deleted"
    assert (
        getattr(deleted_record, "deleted_at") is not None
    ), "Record should have a deletion timestamp"


@pytest.mark.asyncio
async def test_soft_delete_custom_columns(async_session, test_model, test_data):
    crud = FastCRUD(
        test_model,
        is_deleted_column="custom_is_deleted",
        deleted_at_column="custom_deleted_at",
    )
    for item in test_data:
        async_session.add(test_model(**item))
    await async_session.commit()

    existing_record = await crud.get(async_session, id=test_data[0]["id"])
    assert existing_record is not None, "Record should exist before deletion"

    await crud.delete(async_session, id=test_data[0]["id"], allow_multiple=False)

    deleted_record = await crud.get(async_session, id=test_data[0]["id"])
    assert (
        deleted_record is None
    ), "Custom columns not found, so record should be deleted."


@pytest.mark.asyncio
async def test_db_delete_disallow_multiple_matches(
    async_session, test_data, test_model
):
    tier_id_for_multiple_records = 1
    for item in test_data:
        async_session.add(test_model(**item))
    await async_session.commit()

    crud = FastCRUD(test_model)

    with pytest.raises(MultipleResultsFound):
        await crud.db_delete(
            db=async_session, allow_multiple=False, tier_id=tier_id_for_multiple_records
        )

    remaining_records = await async_session.execute(
        select(test_model).where(test_model.tier_id == tier_id_for_multiple_records)
    )
    assert remaining_records.scalars().all(), "No records should have been deleted"


@pytest.mark.asyncio
async def test_soft_delete_db_row_provided(async_session, test_data, test_model):
    test_record = test_model(**test_data[0])
    async_session.add(test_record)
    await async_session.commit()

    crud = FastCRUD(
        test_model, is_deleted_column="is_deleted", deleted_at_column="deleted_at"
    )

    db_row = await async_session.get(test_model, test_record.id)

    await crud.delete(db=async_session, db_row=db_row)

    soft_deleted_record = await async_session.get(test_model, test_record.id)
    assert soft_deleted_record.is_deleted
    assert soft_deleted_record.deleted_at is not None


@pytest.mark.asyncio
async def test_hard_delete_db_row_provided(async_session, test_data_tier, tier_model):
    test_record = tier_model(**test_data_tier[0])
    async_session.add(test_record)
    await async_session.commit()

    crud = FastCRUD(tier_model)
    db_row = await async_session.get(tier_model, test_record.id)

    await crud.delete(db=async_session, db_row=db_row)

    deleted_record = await async_session.get(tier_model, test_record.id)
    assert deleted_record is None


@pytest.mark.asyncio
async def test_delete_no_records_match_filters_raises_no_result_found(
    async_session, test_data, test_model
):
    crud = FastCRUD(test_model)
    non_matching_filter_criteria = {"id": 99999} # Using as extra_filters via kwargs

    with pytest.raises(NoResultFound):
        await crud.delete(db=async_session, **non_matching_filter_criteria)


# New tests for the `delete` method with updated signature

@pytest.mark.asyncio
async def test_delete_with_filters_param_soft_delete(async_session, test_data, test_model):
    for item in test_data:
        async_session.add(test_model(**item))
    await async_session.commit()

    crud = FastCRUD(test_model)
    item_to_delete_id = test_data[0]["id"]
    delete_filter = ItemDeleteSchema(id=item_to_delete_id)

    await crud.delete(db=async_session, filters=delete_filter)

    deleted_record_query = await async_session.execute(
        select(test_model).where(test_model.id == item_to_delete_id)
    )
    deleted_record = deleted_record_query.scalar_one()
    assert deleted_record.is_deleted is True
    assert deleted_record.deleted_at is not None


@pytest.mark.asyncio
async def test_delete_with_extra_filters_param_soft_delete(async_session, test_data, test_model):
    for item in test_data:
        async_session.add(test_model(**item))
    await async_session.commit()

    crud = FastCRUD(test_model)
    item_to_delete_id = test_data[0]["id"]

    await crud.delete(db=async_session, extra_filters={'id': item_to_delete_id})

    deleted_record_query = await async_session.execute(
        select(test_model).where(test_model.id == item_to_delete_id)
    )
    deleted_record = deleted_record_query.scalar_one()
    assert deleted_record.is_deleted is True
    assert deleted_record.deleted_at is not None


@pytest.mark.asyncio
async def test_delete_with_kwargs_as_extra_filters_soft_delete(async_session, test_data, test_model):
    for item in test_data:
        async_session.add(test_model(**item))
    await async_session.commit()

    crud = FastCRUD(test_model)
    item_to_delete_id = test_data[0]["id"]

    await crud.delete(db=async_session, id=item_to_delete_id) # id= is captured by **extra_filters

    deleted_record_query = await async_session.execute(
        select(test_model).where(test_model.id == item_to_delete_id)
    )
    deleted_record = deleted_record_query.scalar_one()
    assert deleted_record.is_deleted is True
    assert deleted_record.deleted_at is not None


@pytest.mark.asyncio
async def test_delete_with_filters_and_extra_filters_merge_soft_delete(async_session, test_data, test_model):
    # Add specific item to test merge
    item_to_target = {"id": 100, "name": "Mergable", "tier_id": 1, "is_deleted": False}
    async_session.add(test_model(**item_to_target))
    await async_session.commit()

    crud = FastCRUD(test_model)
    # `filters` provides id, `extra_filters` provides name, both should apply.
    # If extra_filters had 'id', it would override the one in `filters`.
    # Here, we test complementing filters.
    delete_schema_filter = ItemDeleteSchema(id=item_to_target["id"])
    extra_filter_criteria = {'name': item_to_target["name"]}

    await crud.delete(db=async_session, filters=delete_schema_filter, extra_filters=extra_filter_criteria)

    deleted_record_query = await async_session.execute(
        select(test_model).where(test_model.id == item_to_target["id"])
    )
    deleted_record = deleted_record_query.scalar_one()
    assert deleted_record.is_deleted is True, "Record should be soft deleted"

    # Test extra_filters overriding filters
    item_to_target_override = {"id": 101, "name": "OverrideTest", "tier_id": 1, "is_deleted": False}
    item_false_positive = {"id": 102, "name": "OriginalName", "tier_id": 1, "is_deleted": False}
    async_session.add(test_model(**item_to_target_override))
    async_session.add(test_model(**item_false_positive))
    await async_session.commit()

    delete_schema_filter_override = ItemDeleteSchema(id=item_false_positive["id"], name="OriginalName") # This would match item_false_positive
    # extra_filters will override 'id' and 'name'
    extra_filter_criteria_override = {'id': item_to_target_override["id"], 'name': "OverrideTest"}

    await crud.delete(db=async_session, filters=delete_schema_filter_override, extra_filters=extra_filter_criteria_override)

    # Check target was deleted
    deleted_record_override_query = await async_session.execute(
        select(test_model).where(test_model.id == item_to_target_override["id"])
    )
    deleted_record_override = deleted_record_override_query.scalar_one()
    assert deleted_record_override.is_deleted is True, "Target record for override test should be soft deleted"

    # Check false positive was NOT deleted
    not_deleted_record_query = await async_session.execute(
        select(test_model).where(test_model.id == item_false_positive["id"])
    )
    not_deleted_record = not_deleted_record_query.scalar_one()
    assert not_deleted_record.is_deleted is False, "False positive record should NOT be soft deleted"


@pytest.mark.asyncio
async def test_delete_value_error_no_filters_or_db_row(async_session, test_model):
    crud = FastCRUD(test_model)
    with pytest.raises(ValueError, match="No filters provided for delete operation."):
        await crud.delete(db=async_session)


@pytest.mark.asyncio
async def test_delete_hard_delete_fallback_with_filters_param(async_session, test_data_tier, tier_model):
    for tier_item in test_data_tier:
        async_session.add(tier_model(**tier_item))
    await async_session.commit()

    crud = FastCRUD(tier_model)
    tier_to_delete_id = test_data_tier[0]["id"]
    delete_filter = TierDeleteSchema(id=tier_to_delete_id)

    await crud.delete(db=async_session, filters=delete_filter)

    deleted_record_query = await async_session.execute(
        select(tier_model).where(tier_model.id == tier_to_delete_id)
    )
    assert deleted_record_query.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_delete_allow_multiple_true_with_filters_param(async_session, test_data, test_model):
    for item in test_data: # Assuming test_data has multiple items with tier_id=1
        async_session.add(test_model(**item))
    await async_session.commit()

    crud = FastCRUD(test_model)
    delete_filter = ItemDeleteSchema(tier_id=1) # tier_id=1 matches multiple records in test_data

    await crud.delete(db=async_session, filters=delete_filter, allow_multiple=True)

    deleted_records_query = await async_session.execute(
        select(test_model).where(test_model.tier_id == 1)
    )
    deleted_records = deleted_records_query.scalars().all()
    assert len(deleted_records) > 0, "Some records should have been found"
    for record in deleted_records:
        assert record.is_deleted is True


@pytest.mark.asyncio
async def test_delete_allow_multiple_false_multiple_results_raises_with_filters_param(async_session, test_data, test_model):
    for item in test_data:
        async_session.add(test_model(**item))
    await async_session.commit()

    crud = FastCRUD(test_model)
    delete_filter = ItemDeleteSchema(tier_id=1) # tier_id=1 matches multiple records

    with pytest.raises(MultipleResultsFound):
        await crud.delete(db=async_session, filters=delete_filter, allow_multiple=False)


@pytest.mark.asyncio
async def test_delete_no_result_found_raises_with_filters_param(async_session, test_model):
    crud = FastCRUD(test_model)
    delete_filter = ItemDeleteSchema(id=99999) # Non-existent ID

    with pytest.raises(NoResultFound):
        await crud.delete(db=async_session, filters=delete_filter)


# New tests for the `db_delete` method with updated signature

@pytest.mark.asyncio
async def test_db_delete_with_filters_param(async_session, test_data_tier, tier_model):
    for tier_item in test_data_tier:
        async_session.add(tier_model(**tier_item))
    await async_session.commit()

    crud = FastCRUD(tier_model)
    tier_to_delete_id = test_data_tier[0]["id"]
    delete_filter = TierDeleteSchema(id=tier_to_delete_id)

    await crud.db_delete(db=async_session, filters=delete_filter)

    deleted_record_query = await async_session.execute(
        select(tier_model).where(tier_model.id == tier_to_delete_id)
    )
    assert deleted_record_query.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_db_delete_with_extra_filters_param(async_session, test_data_tier, tier_model):
    for tier_item in test_data_tier:
        async_session.add(tier_model(**tier_item))
    await async_session.commit()

    crud = FastCRUD(tier_model)
    tier_to_delete_id = test_data_tier[0]["id"]

    await crud.db_delete(db=async_session, extra_filters={'id': tier_to_delete_id})

    deleted_record_query = await async_session.execute(
        select(tier_model).where(tier_model.id == tier_to_delete_id)
    )
    assert deleted_record_query.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_db_delete_with_kwargs_as_extra_filters(async_session, test_data_tier, tier_model):
    for tier_item in test_data_tier:
        async_session.add(tier_model(**tier_item))
    await async_session.commit()

    crud = FastCRUD(tier_model)
    tier_to_delete_id = test_data_tier[0]["id"]

    await crud.db_delete(db=async_session, id=tier_to_delete_id) # id= is captured by **extra_filters

    deleted_record_query = await async_session.execute(
        select(tier_model).where(tier_model.id == tier_to_delete_id)
    )
    assert deleted_record_query.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_db_delete_with_filters_and_extra_filters_merge(async_session, test_data_tier, tier_model):
    # Add specific tier to test merge
    tier_to_target = {"id": 100, "name": "MergableTier"}
    async_session.add(tier_model(**tier_to_target))
    await async_session.commit()

    crud = FastCRUD(tier_model)
    # `filters` provides id, `extra_filters` provides name.
    delete_schema_filter = TierDeleteSchema(id=tier_to_target["id"])
    extra_filter_criteria = {'name': tier_to_target["name"]}

    await crud.db_delete(db=async_session, filters=delete_schema_filter, extra_filters=extra_filter_criteria)

    deleted_record_query = await async_session.execute(
        select(tier_model).where(tier_model.id == tier_to_target["id"])
    )
    assert deleted_record_query.scalar_one_or_none() is None, "Record should be hard deleted"

    # Test extra_filters overriding filters
    tier_to_target_override = {"id": 101, "name": "OverrideTierName"}
    tier_false_positive = {"id": 102, "name": "OriginalTierName"}
    async_session.add(tier_model(**tier_to_target_override))
    async_session.add(tier_model(**tier_false_positive))
    await async_session.commit()
    
    delete_schema_filter_override = TierDeleteSchema(id=tier_false_positive["id"], name="OriginalTierName")
    extra_filter_criteria_override = {'id': tier_to_target_override["id"], 'name': "OverrideTierName"}

    await crud.db_delete(db=async_session, filters=delete_schema_filter_override, extra_filters=extra_filter_criteria_override)

    # Check target was deleted
    deleted_override_query = await async_session.execute(
        select(tier_model).where(tier_model.id == tier_to_target_override["id"])
    )
    assert deleted_override_query.scalar_one_or_none() is None

    # Check false positive was NOT deleted
    not_deleted_query = await async_session.execute(
        select(tier_model).where(tier_model.id == tier_false_positive["id"])
    )
    assert not_deleted_query.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_db_delete_value_error_no_filters(async_session, tier_model):
    crud = FastCRUD(tier_model)
    with pytest.raises(ValueError, match="No filters provided for db_delete operation."):
        await crud.db_delete(db=async_session)


@pytest.mark.asyncio
async def test_db_delete_allow_multiple_true_with_filters_param(async_session, test_data_tier, tier_model):
    # Ensure multiple records match the criteria, e.g., all records if no specific filter is too narrow
    for tier_item in test_data_tier: # Assuming test_data_tier has multiple items
        async_session.add(tier_model(**tier_item))
    await async_session.commit()

    crud = FastCRUD(tier_model)
    # Using a filter that matches all initially added test_data_tier items if they share a common, deletable characteristic
    # For simplicity, if test_data_tier items are few, we can delete by a common characteristic or all.
    # Here, we'll delete all items with name "Test Tier" which should be all of them based on conftest.
    delete_filter = TierDeleteSchema(name="Test Tier")

    await crud.db_delete(db=async_session, filters=delete_filter, allow_multiple=True)

    deleted_records_query = await async_session.execute(
        select(tier_model).where(tier_model.name == "Test Tier")
    )
    assert len(deleted_records_query.scalars().all()) == 0


@pytest.mark.asyncio
async def test_db_delete_allow_multiple_false_multiple_results_raises_with_filters_param(async_session, test_data_tier, tier_model):
    for tier_item in test_data_tier: # tier_model data usually has multiple 'Test Tier'
        async_session.add(tier_model(**tier_item))
    await async_session.commit()

    crud = FastCRUD(tier_model)
    delete_filter = TierDeleteSchema(name="Test Tier") # This will match multiple records

    with pytest.raises(MultipleResultsFound):
        await crud.db_delete(db=async_session, filters=delete_filter, allow_multiple=False)


@pytest.mark.asyncio
async def test_db_delete_no_records_match_does_not_raise_no_result_found_with_filters_param(async_session, tier_model):
    crud = FastCRUD(tier_model)
    delete_filter = TierDeleteSchema(id=87654) # Non-existent ID

    try:
        await crud.db_delete(db=async_session, filters=delete_filter)
    except NoResultFound:
        pytest.fail("db_delete should not raise NoResultFound when no records match the criteria.")
    
    # Verify no records were actually there or deleted (optional check)
    count = await crud.count(db=async_session, id=87654)
    assert count == 0
