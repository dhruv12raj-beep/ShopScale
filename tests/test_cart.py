from decimal import Decimal

PASSWORD = "supersecret123"


async def auth_headers(client, email="alice@example.com"):
    await client.post(
        "/api/v1/auth/register", json={"email": email, "password": PASSWORD}
    )
    token = (
        await client.post(
            "/api/v1/auth/login", data={"username": email, "password": PASSWORD}
        )
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def create_product(client, stock=5):
    response = await client.post(
        "/api/v1/products", json={"name": "Mouse", "price": "10.00", "stock": stock}
    )
    return response.json()["id"]


async def test_add_to_cart(client):
    headers = await auth_headers(client)
    product_id = await create_product(client)
    response = await client.post(
        "/api/v1/cart/items",
        json={"product_id": product_id, "quantity": 2},
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["quantity"] == 2
    assert Decimal(body["total"]) == Decimal("20.00")


async def test_add_to_cart_requires_login(client):
    product_id = await create_product(client)
    response = await client.post(
        "/api/v1/cart/items", json={"product_id": product_id, "quantity": 1}
    )
    assert response.status_code == 401


async def test_add_same_product_twice_increments(client):
    headers = await auth_headers(client)
    product_id = await create_product(client)
    await client.post(
        "/api/v1/cart/items", json={"product_id": product_id, "quantity": 1}, headers=headers
    )
    response = await client.post(
        "/api/v1/cart/items", json={"product_id": product_id, "quantity": 2}, headers=headers
    )
    assert response.status_code == 201
    assert response.json()["items"][0]["quantity"] == 3


async def test_add_unknown_product(client):
    headers = await auth_headers(client)
    response = await client.post(
        "/api/v1/cart/items", json={"product_id": 999, "quantity": 1}, headers=headers
    )
    assert response.status_code == 404


async def test_add_exceeds_stock(client):
    headers = await auth_headers(client)
    product_id = await create_product(client, stock=3)
    response = await client.post(
        "/api/v1/cart/items", json={"product_id": product_id, "quantity": 5}, headers=headers
    )
    assert response.status_code == 409


async def test_cannot_see_other_users_cart(client):
    alice = await auth_headers(client, "alice@example.com")
    bob = await auth_headers(client, "bob@example.com")
    product_id = await create_product(client)
    await client.post(
        "/api/v1/cart/items", json={"product_id": product_id, "quantity": 1}, headers=alice
    )
    response = await client.get("/api/v1/cart", headers=bob)
    assert response.status_code == 200
    assert response.json()["items"] == []


async def test_update_quantity(client):
    headers = await auth_headers(client)
    product_id = await create_product(client)
    await client.post(
        "/api/v1/cart/items", json={"product_id": product_id, "quantity": 1}, headers=headers
    )
    response = await client.patch(
        f"/api/v1/cart/items/{product_id}", json={"quantity": 3}, headers=headers
    )
    assert response.status_code == 200
    assert response.json()["items"][0]["quantity"] == 3


async def test_update_item_not_in_cart(client):
    headers = await auth_headers(client)
    product_id = await create_product(client)
    response = await client.patch(
        f"/api/v1/cart/items/{product_id}", json={"quantity": 2}, headers=headers
    )
    assert response.status_code == 404


async def test_remove_item(client):
    headers = await auth_headers(client)
    product_id = await create_product(client)
    await client.post(
        "/api/v1/cart/items", json={"product_id": product_id, "quantity": 1}, headers=headers
    )
    response = await client.delete(f"/api/v1/cart/items/{product_id}", headers=headers)
    assert response.status_code == 204
    assert (await client.get("/api/v1/cart", headers=headers)).json()["items"] == []


async def test_clear_cart(client):
    headers = await auth_headers(client)
    p1 = await create_product(client)
    p2 = await create_product(client)
    for pid in (p1, p2):
        await client.post(
            "/api/v1/cart/items", json={"product_id": pid, "quantity": 1}, headers=headers
        )
    response = await client.delete("/api/v1/cart", headers=headers)
    assert response.status_code == 204
    body = (await client.get("/api/v1/cart", headers=headers)).json()
    assert body["items"] == []
    assert Decimal(body["total"]) == Decimal("0")