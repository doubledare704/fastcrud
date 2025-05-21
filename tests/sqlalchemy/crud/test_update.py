from datetime import datetime, timezone
import pytest

from sqlalchemy import select
from sqlalchemy.exc import MultipleResultsFound, NoResultFound

from fastcrud.crud.fast_crud import FastCRUD
from ...sqlalchemy.conftest import ModelTest, UpdateSchemaTest, ModelTestWithTimestamp


@pytest.mark.asyncio
async def test_update_successful(async_session, test_data):
    for item in test_data:
        async_session.add(ModelTest(**item))
    await async_session.commit()

    crud = FastCRUD(ModelTest)
    some_existing_id = test_data[0]["id"]
    updated_data = {"name": "Updated Name"}
    await crud.update(db=async_session, object=updated_data, id=some_existing_id)

    updated_record = await async_session.execute(
        select(ModelTest).where(ModelTest.id == some_existing_id)
    )
    assert updated_record.scalar_one().name == "Updated Name"


@pytest.mark.asyncio
async def test_update_various_data(async_session, test_data):
    for item in test_data:
        async_session.add(ModelTest(**item))
    await async_session.commit()

    crud = FastCRUD(ModelTest)
    some_existing_id = test_data[0]["id"]
    updated_data = {"name": "Different Name"}
    await crud.update(db=async_session, object=updated_data, id=some_existing_id)

    updated_record = await async_session.execute(
        select(ModelTest).where(ModelTest.id == some_existing_id)
    )
    assert updated_record.scalar_one().name == "Different Name"


@pytest.mark.asyncio
async def test_update_non_existent_record(async_session, test_data):
    for item in test_data:
        async_session.add(ModelTest(**item))
    await async_session.commit()

    crud = FastCRUD(ModelTest)
    non_existent_id = 99999
    updated_data = {"name": "New Name"}

    with pytest.raises(NoResultFound) as exc_info:
        await crud.update(db=async_session, object=updated_data, id=non_existent_id)

    assert "No record found to update" in str(exc_info.value)


@pytest.mark.asyncio
async def test_update_invalid_filters(async_session, test_data):
    for item in test_data:
        async_session.add(ModelTest(**item))
    await async_session.commit()

    crud = FastCRUD(ModelTest)
    updated_data = {"name": "New Name"}

    non_matching_filter = {"name": "NonExistingName"}
    with pytest.raises(NoResultFound) as exc_info:
        await crud.update(db=async_session, object=updated_data, **non_matching_filter)

    assert "No record found to update" in str(exc_info.value)


@pytest.mark.asyncio
async def test_update_additional_fields(async_session, test_data):
    for item in test_data:
        async_session.add(ModelTest(**item))
    await async_session.commit()

    crud = FastCRUD(ModelTest)
    some_existing_id = test_data[0]["id"]
    updated_data = {"name": "Updated Name", "extra_field": "Extra"}

    with pytest.raises(ValueError) as exc_info:
        await crud.update(db=async_session, object=updated_data, id=some_existing_id)

    assert "Extra fields provided" in str(exc_info.value)


@pytest.mark.asyncio
async def test_update_with_advanced_filters(async_session, test_data):
    for item in test_data:
        async_session.add(ModelTest(**item))
    await async_session.commit()

    advanced_filter = {"id__gt": 5}
    updated_data = {"name": "Updated for Advanced Filter"}

    crud = FastCRUD(ModelTest)
    await crud.update(
        db=async_session, object=updated_data, allow_multiple=True, **advanced_filter
    )

    updated_records = await async_session.execute(
        select(ModelTest).where(ModelTest.id > 5)
    )
    assert all(
        record.name == "Updated for Advanced Filter"
        for record in updated_records.scalars()
    )


@pytest.mark.asyncio
async def test_update_multiple_records(async_session, test_data):
    for item in test_data:
        async_session.add(ModelTest(**item))
    await async_session.commit()

    crud = FastCRUD(ModelTest)
    updated_data = {"name": "Updated Multiple"}
    await crud.update(
        db=async_session, object=updated_data, allow_multiple=True, tier_id=2
    )

    updated_records = await async_session.execute(
        select(ModelTest).where(ModelTest.tier_id == 2)
    )
    assert all(
        record.name == "Updated Multiple" for record in updated_records.scalars()
    )


@pytest.mark.asyncio
async def test_update_multiple_records_restriction(async_session, test_data):
    for item in test_data:
        async_session.add(ModelTest(**item))
    await async_session.commit()

    crud = FastCRUD(ModelTest)
    updated_data = {"name": "Should Fail"}

    with pytest.raises(MultipleResultsFound) as exc_info:
        await crud.update(db=async_session, object=updated_data, id__lt=10)

    assert "Expected exactly one record to update" in str(exc_info.value)


@pytest.mark.asyncio
async def test_update_multiple_records_allow_multiple(
    async_session, test_model, test_data
):
    for item in test_data:
        async_session.add(test_model(**item))
    await async_session.commit()

    crud = FastCRUD(test_model)

    await crud.update(
        async_session, {"name": "UpdatedName"}, allow_multiple=True, tier_id=1
    )
    updated_count = await crud.count(async_session, name="UpdatedName")
    expected_count = len([item for item in test_data if item["tier_id"] == 1])

    assert updated_count == expected_count


@pytest.mark.asyncio
async def test_update_with_schema_object(async_session, test_data):
    for item in test_data:
        async_session.add(ModelTest(**item))
    await async_session.commit()

    crud = FastCRUD(ModelTest)
    target_id = test_data[0]["id"]
    update_schema = UpdateSchemaTest(name="Updated Via Schema Object")

    await crud.update(db=async_session, object=update_schema, id=target_id)

    updated_record = await async_session.execute(
        select(ModelTest).where(ModelTest.id == target_id)
    )
    updated = updated_record.scalar_one()
    assert (
        updated.name == "Updated Via Schema Object"
    ), "Record should be updated with the name from the schema object."


@pytest.mark.asyncio
async def test_update_auto_updates_updated_at(async_session, test_data):
    initial_time = datetime.now(timezone.utc)
    test_record = ModelTestWithTimestamp(name="InitialName", updated_at=initial_time)
    async_session.add(test_record)
    await async_session.commit()

    crud = FastCRUD(ModelTestWithTimestamp, updated_at_column="updated_at")
    await crud.update(
        db=async_session, object={"name": "UpdatedName"}, id=test_record.id
    )

    updated_record = await async_session.execute(
        select(ModelTestWithTimestamp).where(
            ModelTestWithTimestamp.id == test_record.id
        )
    )
    updated = updated_record.scalar_one()
    assert updated.name == "UpdatedName", "Record should be updated with the new name."
    assert (
        updated.updated_at > initial_time
    ), "updated_at should be later than the initial timestamp."


@pytest.mark.parametrize(
    ["update_kwargs", "expected_result"],
    [
        pytest.param(
            {"return_columns": ["id", "name"]},
            {
                "id": 1,
                "name": "Updated Name",
            },
            id="dict",
        ),
        pytest.param(
            {"schema_to_select": UpdateSchemaTest, "return_as_model": True},
            UpdateSchemaTest(id=1, name="Updated Name"),
            id="model",
        ),
        pytest.param(
            {"allow_multiple": True, "return_columns": ["id", "name"]},
            {
                "data": [
                    {
                        "id": 1,
                        "name": "Updated Name",
                    }
                ]
            },
            id="multiple_dict",
        ),
        pytest.param(
            {
                "allow_multiple": True,
                "schema_to_select": UpdateSchemaTest,
                "return_as_model": True,
            },
            {"data": [UpdateSchemaTest(id=1, name="Updated Name")]},
            id="multiple_model",
        ),
    ],
)
@pytest.mark.asyncio
async def test_update_with_returning(
    async_session, test_data, update_kwargs, expected_result
):
    # Ensure test_data has 'id': 1 for this test
    test_data_with_id_1 = [item for item in test_data if item["id"] == 1]
    if not test_data_with_id_1:
        test_data_with_id_1 = [{"id": 1, "name": "Initial Name", "tier_id": 1}] # Add if missing
    
    for item in test_data_with_id_1: # Use filtered or supplemented data
        existing = await async_session.get(ModelTest, item["id"])
        if not existing:
            async_session.add(ModelTest(**item))
    await async_session.commit()

    crud = FastCRUD(ModelTest)
    target_id = 1 # Consistently use ID 1
    updated_data = {"name": "Updated Name"}

    # Ensure UpdateSchemaTest can handle 'id' if it's part of the expected model output
    if "return_as_model" in update_kwargs and update_kwargs["return_as_model"]:
        if not hasattr(UpdateSchemaTest, "id"):
            # Monkey patch for testing if necessary, or adjust schema
            UpdateSchemaTest.model_fields["id"] = UpdateSchemaTest.model_fields.get("id", int)


    updated_record = await crud.update(
        db=async_session,
        object=updated_data,
        id=target_id,
        **update_kwargs,
    )

    assert updated_record == expected_result

    # Rollback the current transaction to see if the record was actually committed
    # This part of the test might be problematic if the update wasn't committed within the method
    # If the crud.update commits internally (based on commit=True default), then rollback here is fine.
    await async_session.rollback() 
    
    # Verify the state *before* rollback if commit=False was intended for the update
    # However, the default is commit=True.
    # This assertion checks if the change persisted, implying commit=True worked.
    
    # Re-fetch to check committed state if needed, but count is simpler
    count = await crud.count(async_session, name="Updated Name", id=target_id)
    assert count == 1


from ...sqlalchemy.conftest import UserTest, TagTest, UserTestCreate, TagTestCreate, UserTestRead, UserTestUpdateWithTags

@pytest.mark.asyncio
class TestUpdateManyToManySQLAlchemy:
    @pytest.fixture(autouse=True)
    async def setup_method(self, async_session):
        # Clean up tables before each test if necessary, or rely on transaction rollbacks
        pass

    async def _create_user_and_tags(self, async_session, user_name="Test User", tag_names=["TagA", "TagB"]):
        user_crud = FastCRUD(UserTest)
        tag_crud = FastCRUD(TagTest)

        user = await user_crud.create(async_session, UserTestCreate(name=user_name))
        tags = []
        for name in tag_names:
            tags.append(await tag_crud.create(async_session, TagTestCreate(name=name)))
        await async_session.commit()
        return user, tags

    async def test_add_new_relationships(self, async_session):
        user, tags = await self._create_user_and_tags(async_session)
        user_crud = FastCRUD(UserTest)

        tag_ids = [tag.id for tag in tags]
        await user_crud.update(async_session, {"tags": tag_ids}, id=user.id)
        await async_session.commit() # Ensure commit after update

        updated_user = await user_crud.get(async_session, schema_to_select=UserTestRead, return_as_model=True, id=user.id)
        assert updated_user is not None
        assert len(updated_user.tags) == len(tag_ids)
        assert sorted([tag.id for tag in updated_user.tags]) == sorted(tag_ids)

    async def test_replace_existing_relationships(self, async_session):
        user, initial_tags = await self._create_user_and_tags(async_session, tag_names=["Tag1", "Tag2"])
        user_crud = FastCRUD(UserTest)
        tag_crud = FastCRUD(TagTest)

        # Set initial tags
        await user_crud.update(async_session, {"tags": [tag.id for tag in initial_tags]}, id=user.id)
        await async_session.commit()

        # Create new tags
        new_tags_data = [TagTestCreate(name="Tag3"), TagTestCreate(name="Tag4")]
        new_tags = [await tag_crud.create(async_session, nt) for nt in new_tags_data]
        await async_session.commit()
        new_tag_ids = [tag.id for tag in new_tags]

        await user_crud.update(async_session, {"tags": new_tag_ids}, id=user.id)
        await async_session.commit()

        updated_user = await user_crud.get(async_session, schema_to_select=UserTestRead, return_as_model=True, id=user.id)
        assert updated_user is not None
        assert len(updated_user.tags) == len(new_tag_ids)
        assert sorted([tag.id for tag in updated_user.tags]) == sorted(new_tag_ids)

    async def test_remove_all_relationships(self, async_session):
        user, tags = await self._create_user_and_tags(async_session, tag_names=["TagX", "TagY"])
        user_crud = FastCRUD(UserTest)

        await user_crud.update(async_session, {"tags": [tag.id for tag in tags]}, id=user.id)
        await async_session.commit()

        await user_crud.update(async_session, {"tags": []}, id=user.id)
        await async_session.commit()
        
        updated_user = await user_crud.get(async_session, schema_to_select=UserTestRead, return_as_model=True, id=user.id)
        assert updated_user is not None
        assert len(updated_user.tags) == 0

    async def test_update_relationships_and_attributes_simultaneously(self, async_session):
        user, tags = await self._create_user_and_tags(async_session)
        user_crud = FastCRUD(UserTest)
        tag_crud = FastCRUD(TagTest)

        new_name = "Updated User Name"
        
        # New tags for update
        new_tags_data = [TagTestCreate(name="TagC"), TagTestCreate(name="TagD")]
        new_tags = [await tag_crud.create(async_session, nt) for nt in new_tags_data]
        await async_session.commit()
        new_tag_ids = [tag.id for tag in new_tags]

        update_payload = UserTestUpdateWithTags(name=new_name, tags=new_tag_ids)
        await user_crud.update(async_session, update_payload, id=user.id)
        await async_session.commit()

        updated_user = await user_crud.get(async_session, schema_to_select=UserTestRead, return_as_model=True, id=user.id)
        assert updated_user is not None
        assert updated_user.name == new_name
        assert len(updated_user.tags) == len(new_tag_ids)
        assert sorted([tag.id for tag in updated_user.tags]) == sorted(new_tag_ids)

    async def test_attempt_add_non_existent_related_ids(self, async_session):
        user, _ = await self._create_user_and_tags(async_session, tag_names=[])
        user_crud = FastCRUD(UserTest)

        non_existent_tag_id = 9999
        with pytest.raises(ValueError) as exc_info:
            await user_crud.update(async_session, {"tags": [non_existent_tag_id]}, id=user.id)
        
        assert f"Related objects not found for IDs: {{{non_existent_tag_id}}} in tags" in str(exc_info.value)

    async def test_update_m2m_with_return_columns_and_model(self, async_session):
        user, tags = await self._create_user_and_tags(async_session)
        user_crud = FastCRUD(UserTest)
        tag_crud = FastCRUD(TagTest)
        
        new_tag_data = TagTestCreate(name="ReturnTag")
        new_tag = await tag_crud.create(async_session, new_tag_data)
        await async_session.commit()
        new_tag_ids = [new_tag.id]

        update_payload = {"name": "Returned User", "tags": new_tag_ids}
        
        # Test with return_as_model=True
        returned_data_model = await user_crud.update(
            async_session, 
            update_payload, 
            id=user.id, 
            schema_to_select=UserTestRead, 
            return_as_model=True
        )
        await async_session.commit() # Ensure commit after update

        assert isinstance(returned_data_model, UserTestRead)
        assert returned_data_model.name == "Returned User"
        # The returned model from update might not have M2M relationships loaded by default
        # unless the schema_to_select is designed for it and the update method populates it.
        # Current update method implementation re-fetches if only M2M and return_columns.
        # If columns and M2M updated, it returns based on .returning() for columns.
        # Let's verify the DB state for M2M.
        
        db_user = await user_crud.get(async_session, schema_to_select=UserTestRead, return_as_model=True, id=user.id)
        assert db_user is not None
        assert len(db_user.tags) == len(new_tag_ids)
        assert db_user.tags[0].id == new_tag.id
        assert db_user.tags[0].name == "ReturnTag"

        # Test with return_columns (focused on direct columns)
        tag_crud = FastCRUD(TagTest) # Re-init just in case
        another_new_tag = await tag_crud.create(async_session, TagTestCreate(name="AnotherReturnTag"))
        await async_session.commit()
        
        another_new_tag_ids = [another_new_tag.id]
        update_payload_2 = {"name": "Returned User Again", "tags": another_new_tag_ids}

        returned_data_dict = await user_crud.update(
            async_session, 
            update_payload_2, 
            id=user.id, 
            return_columns=["id", "name"]
        )
        await async_session.commit()

        assert isinstance(returned_data_dict, dict)
        assert returned_data_dict["name"] == "Returned User Again"
        assert "tags" not in returned_data_dict # Tags are not direct columns

        db_user_again = await user_crud.get(async_session, schema_to_select=UserTestRead, return_as_model=True, id=user.id)
        assert db_user_again is not None
        assert len(db_user_again.tags) == len(another_new_tag_ids)
        assert db_user_again.tags[0].id == another_new_tag.id

    async def test_update_m2m_only_relationships_return_model(self, async_session):
        user, initial_tags = await self._create_user_and_tags(async_session, tag_names=["InitialTag"])
        user_crud = FastCRUD(UserTest)
        tag_crud = FastCRUD(TagTest)

        # Set initial tags
        await user_crud.update(async_session, {"tags": [tag.id for tag in initial_tags]}, id=user.id)
        await async_session.commit()

        # New tags for update
        new_tags_data = [TagTestCreate(name="NewTag1"), TagTestCreate(name="NewTag2")]
        new_tags = [await tag_crud.create(async_session, nt) for nt in new_tags_data]
        await async_session.commit()
        new_tag_ids = [tag.id for tag in new_tags]

        # Update only tags, but request model return
        returned_model = await user_crud.update(
            async_session,
            {"tags": new_tag_ids},
            id=user.id,
            schema_to_select=UserTestRead,
            return_as_model=True
        )
        await async_session.commit()

        assert isinstance(returned_model, UserTestRead)
        assert returned_model.id == user.id
        assert returned_model.name == user.name # Name should be unchanged

        # Verify relationships in the returned model (depends on re-fetch logic)
        # The current implementation should re-fetch the model if only M2M are updated and model is returned.
        assert len(returned_model.tags) == len(new_tag_ids)
        assert sorted([t.id for t in returned_model.tags]) == sorted(new_tag_ids)

        # Also verify directly from DB
        db_user = await user_crud.get(async_session, schema_to_select=UserTestRead, return_as_model=True, id=user.id)
        assert db_user is not None
        assert len(db_user.tags) == len(new_tag_ids)
        assert sorted([t.id for t in db_user.tags]) == sorted(new_tag_ids)

    async def test_update_m2m_allow_multiple(self, async_session):
        user_crud = FastCRUD(UserTest)
        tag_crud = FastCRUD(TagTest)

        user1 = await user_crud.create(async_session, UserTestCreate(name="UserFoo"))
        user2 = await user_crud.create(async_session, UserTestCreate(name="UserFoo")) # Same name for filtering
        await async_session.commit()

        tag1 = await tag_crud.create(async_session, TagTestCreate(name="MultiTagA"))
        tag2 = await tag_crud.create(async_session, TagTestCreate(name="MultiTagB"))
        await async_session.commit()
        tag_ids = [tag1.id, tag2.id]

        # Update multiple users matching the name "UserFoo"
        update_result = await user_crud.update(
            async_session,
            {"tags": tag_ids},
            allow_multiple=True,
            name="UserFoo", # Filter criteria
            return_columns=["id", "name"] # Request some columns back
        )
        await async_session.commit()

        assert update_result is not None
        assert "data" in update_result
        assert len(update_result["data"]) == 2 # Assuming two users were named "UserFoo"

        # Verify tags for user1
        updated_user1 = await user_crud.get(async_session, schema_to_select=UserTestRead, return_as_model=True, id=user1.id)
        assert updated_user1 is not None
        assert len(updated_user1.tags) == len(tag_ids)
        assert sorted([tag.id for tag in updated_user1.tags]) == sorted(tag_ids)

        # Verify tags for user2
        updated_user2 = await user_crud.get(async_session, schema_to_select=UserTestRead, return_as_model=True, id=user2.id)
        assert updated_user2 is not None
        assert len(updated_user2.tags) == len(tag_ids)
        assert sorted([tag.id for tag in updated_user2.tags]) == sorted(tag_ids)
