import pytest
from fastapi.testclient import TestClient
from sqlmodel import select, Session as SQLModelSession # Renamed to avoid conflict with pytest 'session'
from fastapi.routing import APIRoute

# Test for soft delete (model with is_deleted)
@pytest.mark.asyncio
async def test_soft_delete_item_sqlmodel(client_hard_delete_disabled_soft_delete_model_sqlmodel: TestClient, async_session: SQLModelSession, test_model, test_data):
    client = client_hard_delete_disabled_soft_delete_model_sqlmodel
    for data_item in test_data:
        item_data = {k: v for k,v in data_item.items() if hasattr(test_model, k)}
        new_item = test_model.model_validate(item_data)
        async_session.add(new_item)
    await async_session.commit()

    result = await async_session.exec(select(test_model).order_by(test_model.id).limit(1))
    item_to_delete = result.first()
    assert item_to_delete is not None
    item_id = item_to_delete.id

    response = client.delete(f"/test_soft_delete_sqlmodel/{item_id}")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data == {"message": "Item deleted successfully"}

    db_item = await async_session.get(test_model, item_id)
    assert db_item is not None
    assert db_item.is_deleted is True


# Test for hard delete when enabled (model with is_deleted)
@pytest.mark.asyncio
async def test_db_delete_item_when_enabled_sqlmodel(client_hard_delete_enabled_soft_delete_model_sqlmodel: TestClient, async_session: SQLModelSession, test_model, test_data):
    client = client_hard_delete_enabled_soft_delete_model_sqlmodel
    for data_item in test_data:
        item_data = {k: v for k,v in data_item.items() if hasattr(test_model, k)}
        new_item = test_model.model_validate(item_data)
        async_session.add(new_item)
    await async_session.commit()

    result = await async_session.exec(select(test_model).order_by(test_model.id).limit(1))
    item_to_delete = result.first()
    assert item_to_delete is not None
    item_id = item_to_delete.id
    
    response = client.delete(f"/test_soft_delete_hd_enabled_sqlmodel/db_delete/{item_id}")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data == {"message": "Item permanently deleted from the database"}

    db_item = await async_session.get(test_model, item_id)
    assert db_item is None


@pytest.mark.asyncio
async def test_hard_delete_endpoint_not_available_by_default_soft_delete_model_sqlmodel(client_hard_delete_disabled_soft_delete_model_sqlmodel: TestClient):
    client = client_hard_delete_disabled_soft_delete_model_sqlmodel
    response = client.delete("/test_soft_delete_sqlmodel/db_delete/1")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_hard_delete_endpoint_not_available_by_default_hard_delete_model_sqlmodel(client_hard_delete_disabled_hard_delete_model_sqlmodel: TestClient):
    client = client_hard_delete_disabled_hard_delete_model_sqlmodel
    response = client.delete("/test_hard_delete_sqlmodel/db_delete/1")
    assert response.status_code == 404


def _check_route_exists_sqlmodel(client: TestClient, path: str, method: str) -> bool:
    for route in client.app.routes:
        if isinstance(route, APIRoute) and route.path == path and method in route.methods:
            return True
    return False

@pytest.mark.asyncio
async def test_hard_delete_endpoint_available_when_flag_is_true_soft_delete_model_sqlmodel(client_hard_delete_enabled_soft_delete_model_sqlmodel: TestClient):
    client = client_hard_delete_enabled_soft_delete_model_sqlmodel
    assert _check_route_exists_sqlmodel(client, "/test_soft_delete_hd_enabled_sqlmodel/db_delete/{id}", "DELETE")


@pytest.mark.asyncio
async def test_hard_delete_endpoint_available_when_flag_is_true_hard_delete_model_sqlmodel(client_hard_delete_enabled_hard_delete_model_sqlmodel: TestClient):
    client = client_hard_delete_enabled_hard_delete_model_sqlmodel
    assert _check_route_exists_sqlmodel(client, "/test_hard_delete_hd_enabled_sqlmodel/db_delete/{id}", "DELETE")


@pytest.mark.asyncio
async def test_hard_delete_endpoint_functionality_hard_delete_model_sqlmodel(
    client_hard_delete_enabled_hard_delete_model_sqlmodel: TestClient, async_session: SQLModelSession, model_hard_delete_sqlmodel, create_schema_hard_delete_sqlmodel
):
    client = client_hard_delete_enabled_hard_delete_model_sqlmodel
    item_data = create_schema_hard_delete_sqlmodel(name="test_item_hard_delete_func_sqlmodel")
    
    response_create = client.post("/test_hard_delete_hd_enabled_sqlmodel/", json=item_data.model_dump())
    assert response_create.status_code == 200, response_create.text
    created_item_id = response_create.json()["id"]

    response_delete = client.delete(f"/test_hard_delete_hd_enabled_sqlmodel/db_delete/{created_item_id}")
    assert response_delete.status_code == 200, response_delete.text
    assert response_delete.json() == {"message": "Item permanently deleted from the database"}

    db_item = await async_session.get(model_hard_delete_sqlmodel, created_item_id)
    assert db_item is None

    response_get = client.get(f"/test_hard_delete_hd_enabled_sqlmodel/{created_item_id}")
    assert response_get.status_code == 404


# OpenAPI Schema Tests for SQLModel
def get_path_operation_description_sqlmodel(openapi_schema: dict, path: str, method: str) -> str | None:
    method_lower = method.lower()
    if path in openapi_schema["paths"] and method_lower in openapi_schema["paths"][path]:
        return openapi_schema["paths"][path][method_lower].get("description")
    return None

@pytest.mark.asyncio
async def test_openapi_standard_delete_description_for_soft_delete_model_sqlmodel(client_hard_delete_disabled_soft_delete_model_sqlmodel: TestClient):
    client = client_hard_delete_disabled_soft_delete_model_sqlmodel
    response = client.get("/openapi.json")
    assert response.status_code == 200
    openapi_schema = response.json()
    
    description = get_path_operation_description_sqlmodel(openapi_schema, "/test_soft_delete_sqlmodel/{id}", "DELETE")
    assert description is not None
    assert "Soft delete" in description
    assert "ModelTest" in description # SQLModel ModelTest

@pytest.mark.asyncio
async def test_openapi_standard_delete_description_for_hard_delete_model_sqlmodel(client_hard_delete_disabled_hard_delete_model_sqlmodel: TestClient):
    client = client_hard_delete_disabled_hard_delete_model_sqlmodel
    response = client.get("/openapi.json")
    assert response.status_code == 200
    openapi_schema = response.json()

    description = get_path_operation_description_sqlmodel(openapi_schema, "/test_hard_delete_sqlmodel/{id}", "DELETE")
    assert description is not None
    assert "Delete a" in description 
    assert "ModelTestHardDeleteSqlmodel" in description

@pytest.mark.asyncio
async def test_openapi_db_delete_description_when_enabled_soft_delete_model_sqlmodel(client_hard_delete_enabled_soft_delete_model_sqlmodel: TestClient):
    client = client_hard_delete_enabled_soft_delete_model_sqlmodel
    response = client.get("/openapi.json")
    assert response.status_code == 200
    openapi_schema = response.json()

    description = get_path_operation_description_sqlmodel(openapi_schema, "/test_soft_delete_hd_enabled_sqlmodel/db_delete/{id}", "DELETE")
    assert description is not None
    assert "Permanently delete" in description
    assert "ModelTest" in description # SQLModel ModelTest

@pytest.mark.asyncio
async def test_openapi_db_delete_description_when_enabled_hard_delete_model_sqlmodel(client_hard_delete_enabled_hard_delete_model_sqlmodel: TestClient):
    client = client_hard_delete_enabled_hard_delete_model_sqlmodel
    response = client.get("/openapi.json")
    assert response.status_code == 200
    openapi_schema = response.json()

    description = get_path_operation_description_sqlmodel(openapi_schema, "/test_hard_delete_hd_enabled_sqlmodel/db_delete/{id}", "DELETE")
    assert description is not None
    assert "Permanently delete" in description
    assert "ModelTestHardDeleteSqlmodel" in description
