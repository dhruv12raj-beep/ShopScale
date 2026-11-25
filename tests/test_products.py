from decimal import Decimal

PRODUCT = {"name": "Test Mouse", "price": "29.99", "stock": 10}


async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_create_product(client, admin_headers):
    response = await client.post("/api/v1/products", json=PRODUCT, headers=admin_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == 1
    assert data["name"] == "Test Mouse"
    assert Decimal(data["price"]) == Decimal("29.99")
    assert data["stock"] == 10


async def test_create_product_requires_admin(client):
    # No token at all
    response = await client.post("/api/v1/products", json=PRODUCT)
    assert response.status_code == 401
    # Logged in, but not an admin
    await client.post(
        "/api/v1/auth/register", json={"email": "eve@example.com", "password": "password123"}
    )
    token = (
        await client.post(
            "/api/v1/auth/login",
            data={"username": "eve@example.com", "password": "password123"},
        )
    ).json()["access_token"]
    response = await client.post(
        "/api/v1/products", json=PRODUCT, headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403


async def test_create_product_rejects_negative_price(client, admin_headers):
    bad = {**PRODUCT, "price": "-5"}
    response = await client.post("/api/v1/products", json=bad, headers=admin_headers)
    assert response.status_code == 422


async def test_list_products_empty(client):
    response = await client.get("/api/v1/products")
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0


async def test_get_product_not_found(client):
    response = await client.get("/api/v1/products/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"


async def test_patch_updates_only_sent_fields(client, admin_headers):
    created = (
        await client.post("/api/v1/products", json=PRODUCT, headers=admin_headers)
    ).json()
    response = await client.patch(
        f"/api/v1/products/{created['id']}",
        json={"price": "19.99"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert Decimal(data["price"]) == Decimal("19.99")
    assert data["name"] == "Test Mouse"


async def test_delete_product(client, admin_headers):
    created = (
        await client.post("/api/v1/products", json=PRODUCT, headers=admin_headers)
    ).json()
    response = await client.delete(
        f"/api/v1/products/{created['id']}", headers=admin_headers
    )
    assert response.status_code == 204
    assert (
        await client.get(f"/api/v1/products/{created['id']}")
    ).status_code == 404


async def test_pagination(client, admin_headers):
    for i in range(3):
        await client.post(
            "/api/v1/products",
            json={"name": f"Item {i}", "price": "1.00", "stock": 1},
            headers=admin_headers,
        )
    response = await client.get("/api/v1/products", params={"limit": 2})
    body = response.json()
    assert len(body["items"]) == 2
    assert body["total"] == 3


async def test_search_is_case_insensitive(client, admin_headers):
    await client.post(
        "/api/v1/products",
        json={"name": "Wireless MOUSE", "price": "9.99", "stock": 1},
        headers=admin_headers,
    )
    response = await client.get("/api/v1/products", params={"search": "mouse"})
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "Wireless MOUSE"


async def test_price_filter(client, admin_headers):
    await client.post(
        "/api/v1/products", json={"name": "Cheap", "price": "1.00", "stock": 1},
        headers=admin_headers,
    )
    await client.post(
        "/api/v1/products", json={"name": "Pricey", "price": "100.00", "stock": 1},
        headers=admin_headers,
    )
    response = await client.get("/api/v1/products", params={"min_price": "50"})
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "Pricey"