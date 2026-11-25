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


async def add_to_cart(client, headers, product_id, quantity=1):
    return await client.post(
        "/api/v1/cart/items",
        json={"product_id": product_id, "quantity": quantity},
        headers=headers,
    )


async def test_checkout_creates_order_and_clears_cart(client, create_product):
    headers = await auth_headers(client)
    product_id = await create_product(stock=5)
    await add_to_cart(client, headers, product_id, quantity=2)

    response = await client.post("/api/v1/orders/checkout", headers=headers)
    assert response.status_code == 201
    order = response.json()
    assert order["status"] == "paid"
    assert Decimal(order["total"]) == Decimal("20.00")
    assert len(order["items"]) == 1
    assert order["items"][0]["quantity"] == 2
    assert Decimal(order["items"][0]["line_total"]) == Decimal("20.00")

    cart = (await client.get("/api/v1/cart", headers=headers)).json()
    assert cart["items"] == []


async def test_checkout_decrements_stock(client, create_product):
    headers = await auth_headers(client)
    product_id = await create_product(stock=5)
    await add_to_cart(client, headers, product_id, quantity=3)
    await client.post("/api/v1/orders/checkout", headers=headers)
    product = (await client.get(f"/api/v1/products/{product_id}")).json()
    assert product["stock"] == 2


async def test_checkout_empty_cart(client):
    headers = await auth_headers(client)
    response = await client.post("/api/v1/orders/checkout", headers=headers)
    assert response.status_code == 400


async def test_checkout_insufficient_stock_rolls_back(client, create_product, admin_headers):
    headers = await auth_headers(client)
    p1 = await create_product(stock=5)
    p2 = await create_product(stock=5)
    await add_to_cart(client, headers, p1, quantity=2)
    await add_to_cart(client, headers, p2, quantity=3)

    # Sneak in and shrink p2's stock — only an admin can do this now!
    await client.patch(f"/api/v1/products/{p2}", json={"stock": 1}, headers=admin_headers)

    response = await client.post("/api/v1/orders/checkout", headers=headers)
    assert response.status_code == 409

    p1_after = (await client.get(f"/api/v1/products/{p1}")).json()
    assert p1_after["stock"] == 5

    cart = (await client.get("/api/v1/cart", headers=headers)).json()
    assert len(cart["items"]) == 2
    orders = (await client.get("/api/v1/orders", headers=headers)).json()
    assert orders == []


async def test_order_items_snapshot_prices(client, create_product, admin_headers):
    headers = await auth_headers(client)
    product_id = await create_product(price="10.00")
    await add_to_cart(client, headers, product_id, quantity=1)
    order = (await client.post("/api/v1/orders/checkout", headers=headers)).json()

    await client.patch(
        f"/api/v1/products/{product_id}", json={"price": "99.00"}, headers=admin_headers
    )
    history = (await client.get("/api/v1/orders", headers=headers)).json()
    assert Decimal(history[0]["items"][0]["price"]) == Decimal("10.00")
    assert Decimal(order["total"]) == Decimal("10.00")


async def test_checkout_requires_login(client):
    response = await client.post("/api/v1/orders/checkout")
    assert response.status_code == 401


async def test_orders_are_private(client, create_product):
    alice = await auth_headers(client, "alice@example.com")
    bob = await auth_headers(client, "bob@example.com")
    product_id = await create_product()
    await add_to_cart(client, alice, product_id)
    order = (await client.post("/api/v1/orders/checkout", headers=alice)).json()

    response = await client.get(f"/api/v1/orders/{order['id']}", headers=bob)
    assert response.status_code == 404
    assert (await client.get("/api/v1/orders", headers=bob)).json() == []


async def test_get_order_not_found(client):
    headers = await auth_headers(client)
    response = await client.get("/api/v1/orders/999", headers=headers)
    assert response.status_code == 404