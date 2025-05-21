import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from fastapi.routing import APIRoute


# Existing test for soft delete (model with is_deleted)
@pytest.mark.asyncio
async def test_soft_delete_item(client_hard_delete_disabled_soft_delete_model: TestClient, async_session, test_model, test_data):
    # Using client_hard_delete_disabled_soft_delete_model which uses ModelTest (with is_deleted)
    # and has add_hard_delete_endpoint=False
    client = client_hard_delete_disabled_soft_delete_model
    for data in test_data:
        # Ensure data is compatible with test_model if it's different from ModelTest
        item_data = {k: v for k, v in data.items() if hasattr(test_model, k)}
        new_item = test_model(**item_data) # Make sure test_model is the one used by the client
        async_session.add(new_item)
    await async_session.commit()

    stmt = select(test_model.id).order_by(test_model.id.asc()).limit(1)
    result = await async_session.execute(stmt)
    item_id = result.scalar_one()

    response = client.delete(f"/test_soft_delete/{item_id}")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data == {"message": "Item deleted successfully"}

    db_item = await async_session.get(test_model, item_id)
    assert db_item is not None
    assert db_item.is_deleted is True


# Existing test for hard delete, adapted for the new flag
@pytest.mark.asyncio
async def test_db_delete_item_when_enabled(client_hard_delete_enabled_soft_delete_model: TestClient, async_session, test_model, test_data):
    # Using client_hard_delete_enabled_soft_delete_model which uses ModelTest (with is_deleted)
    # and has add_hard_delete_endpoint=True
    client = client_hard_delete_enabled_soft_delete_model
    for data in test_data:
        item_data = {k: v for k, v in data.items() if hasattr(test_model, k)}
        new_item = test_model(**item_data)
        async_session.add(new_item)
    await async_session.commit()

    stmt = select(test_model.id).order_by(test_model.id.asc()).limit(1)
    result = await async_session.execute(stmt)
    item_id = result.scalar_one()

    response = client.delete(f"/test_soft_delete_hd_enabled/db_delete/{item_id}")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data == {"message": "Item permanently deleted from the database"}

    db_item = await async_session.get(test_model, item_id)
    assert db_item is None


@pytest.mark.asyncio
async def test_hard_delete_endpoint_not_available_by_default_soft_delete_model(client_hard_delete_disabled_soft_delete_model: TestClient):
    client = client_hard_delete_disabled_soft_delete_model
    response = client.delete("/test_soft_delete/db_delete/1")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_hard_delete_endpoint_not_available_by_default_hard_delete_model(client_hard_delete_disabled_hard_delete_model: TestClient):
    client = client_hard_delete_disabled_hard_delete_model
    response = client.delete("/test_hard_delete/db_delete/1")
    assert response.status_code == 404


def _check_route_exists(client: TestClient, path: str, method: str) -> bool:
    for route in client.app.routes:
        if isinstance(route, APIRoute) and route.path == path and method in route.methods:
            return True
    return False

@pytest.mark.asyncio
async def test_hard_delete_endpoint_available_when_flag_is_true_soft_delete_model(client_hard_delete_enabled_soft_delete_model: TestClient):
    client = client_hard_delete_enabled_soft_delete_model
    assert _check_route_exists(client, "/test_soft_delete_hd_enabled/db_delete/{id}", "DELETE")


@pytest.mark.asyncio
async def test_hard_delete_endpoint_available_when_flag_is_true_hard_delete_model(client_hard_delete_enabled_hard_delete_model: TestClient):
    client = client_hard_delete_enabled_hard_delete_model
    assert _check_route_exists(client, "/test_hard_delete_hd_enabled/db_delete/{id}", "DELETE")


@pytest.mark.asyncio
async def test_hard_delete_endpoint_functionality_hard_delete_model(
    client_hard_delete_enabled_hard_delete_model: TestClient, async_session, model_hard_delete, create_schema_hard_delete
):
    client = client_hard_delete_enabled_hard_delete_model
    item_data = create_schema_hard_delete(name="test_item_hard_delete_func")
    
    # Create item
    response_create = client.post("/test_hard_delete_hd_enabled/", json=item_data.model_dump())
    assert response_create.status_code == 200, response_create.text
    created_item_id = response_create.json()["id"]

    # Hard delete item
    response_delete = client.delete(f"/test_hard_delete_hd_enabled/db_delete/{created_item_id}")
    assert response_delete.status_code == 200, response_delete.text
    assert response_delete.json() == {"message": "Item permanently deleted from the database"}

    # Verify item is deleted
    db_item = await async_session.get(model_hard_delete, created_item_id)
    assert db_item is None

    # Also check GET endpoint for 404
    response_get = client.get(f"/test_hard_delete_hd_enabled/{created_item_id}")
    assert response_get.status_code == 404


# OpenAPI Schema Tests
def get_path_operation_description(openapi_schema: dict, path: str, method: str) -> str | None:
    method_lower = method.lower()
    if path in openapi_schema["paths"] and method_lower in openapi_schema["paths"][path]:
        return openapi_schema["paths"][path][method_lower].get("description")
    return None

@pytest.mark.asyncio
async def test_openapi_standard_delete_description_for_soft_delete_model(client_hard_delete_disabled_soft_delete_model: TestClient):
    client = client_hard_delete_disabled_soft_delete_model
    response = client.get("/openapi.json")
    assert response.status_code == 200
    openapi_schema = response.json()
    
    description = get_path_operation_description(openapi_schema, "/test_soft_delete/{id}", "DELETE")
    assert description is not None
    assert "Soft delete" in description
    assert "ModelTest" in description # Assuming ModelTest is used by this client

@pytest.mark.asyncio
async def test_openapi_standard_delete_description_for_hard_delete_model(client_hard_delete_disabled_hard_delete_model: TestClient):
    client = client_hard_delete_disabled_hard_delete_model
    response = client.get("/openapi.json")
    assert response.status_code == 200
    openapi_schema = response.json()

    description = get_path_operation_description(openapi_schema, "/test_hard_delete/{id}", "DELETE")
    assert description is not None
    assert "Delete a" in description 
    assert "ModelTestHardDelete" in description

@pytest.mark.asyncio
async def test_openapi_db_delete_description_when_enabled_soft_delete_model(client_hard_delete_enabled_soft_delete_model: TestClient):
    client = client_hard_delete_enabled_soft_delete_model
    response = client.get("/openapi.json")
    assert response.status_code == 200
    openapi_schema = response.json()

    description = get_path_operation_description(openapi_schema, "/test_soft_delete_hd_enabled/db_delete/{id}", "DELETE")
    assert description is not None
    assert "Permanently delete" in description
    assert "ModelTest" in description

@pytest.mark.asyncio
async def test_openapi_db_delete_description_when_enabled_hard_delete_model(client_hard_delete_enabled_hard_delete_model: TestClient):
    client = client_hard_delete_enabled_hard_delete_model
    response = client.get("/openapi.json")
    assert response.status_code == 200
    openapi_schema = response.json()

    description = get_path_operation_description(openapi_schema, "/test_hard_delete_hd_enabled/db_delete/{id}", "DELETE")
    assert description is not None
    assert "Permanently delete" in description
    assert "ModelTestHardDelete" in description
