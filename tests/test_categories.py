async def create_category(client, admin_headers, name="Electronics"):
    response = await client.post(
        "/api/v1/categories", json={"name": name}, headers=admin_headers
    )
    return response.json()["id"]


async def test_create_category(client, admin_headers):
    response = await client.post(
        "/api/v1/categories", json={"name": "Electronics"}, headers=admin_headers
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Electronics"


async def test_create_category_requires_login(client):
    response = await client.post("/api/v1/categories", json={"name": "X"})
    assert response.status_code == 401


async def test_create_category_non_admin_gets_403(client):
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
        "/api/v1/categories",
        json={"name": "X"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


async def test_duplicate_category_name(client, admin_headers):
    await create_category(client, admin_headers, "Electronics")
    response = await client.post(
        "/api/v1/categories", json={"name": "Electronics"}, headers=admin_headers
    )
    assert response.status_code == 409


async def test_list_categories_is_alphabetical(client, admin_headers):
    await create_category(client, admin_headers, "Zebra")
    await create_category(client, admin_headers, "Alpha")
    response = await client.get("/api/v1/categories")
    names = [c["name"] for c in response.json()]
    assert names == sorted(names)


async def test_update_category(client, admin_headers):
    cat_id = await create_category(client, admin_headers, "Electronics")
    response = await client.patch(
        f"/api/v1/categories/{cat_id}", json={"name": "Gadgets"}, headers=admin_headers
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Gadgets"


async def test_update_category_not_found(client, admin_headers):
    response = await client.patch(
        "/api/v1/categories/999", json={"name": "X"}, headers=admin_headers
    )
    assert response.status_code == 404


async def test_delete_category(client, admin_headers):
    cat_id = await create_category(client, admin_headers, "Electronics")
    response = await client.delete(f"/api/v1/categories/{cat_id}", headers=admin_headers)
    assert response.status_code == 204
    assert (await client.get("/api/v1/categories")).json() == []


async def test_product_with_categories(client, admin_headers):
    cat_id = await create_category(client, admin_headers, "Electronics")
    response = await client.post(
        "/api/v1/products",
        json={"name": "Mouse", "price": "10.00", "stock": 5, "category_ids": [cat_id]},
        headers=admin_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data["categories"]) == 1
    assert data["categories"][0]["name"] == "Electronics"


async def test_product_with_unknown_category(client, admin_headers):
    response = await client.post(
        "/api/v1/products",
        json={"name": "Mouse", "price": "10.00", "stock": 5, "category_ids": [999]},
        headers=admin_headers,
    )
    assert response.status_code == 404


async def test_filter_products_by_category(client, admin_headers):
    electronics = await create_category(client, admin_headers, "Electronics")
    books = await create_category(client, admin_headers, "Books")
    await client.post(
        "/api/v1/products",
        json={"name": "Mouse", "price": "10.00", "stock": 5, "category_ids": [electronics]},
        headers=admin_headers,
    )
    await client.post(
        "/api/v1/products",
        json={"name": "Novel", "price": "5.00", "stock": 5, "category_ids": [books]},
        headers=admin_headers,
    )

    response = await client.get("/api/v1/products", params={"category_id": electronics})
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "Mouse"


async def test_update_replaces_categories(client, admin_headers):
    c1 = await create_category(client, admin_headers, "Electronics")
    c2 = await create_category(client, admin_headers, "Gaming")
    created = (
        await client.post(
            "/api/v1/products",
            json={"name": "Mouse", "price": "10.00", "stock": 5, "category_ids": [c1]},
            headers=admin_headers,
        )
    ).json()
    response = await client.patch(
        f"/api/v1/products/{created['id']}",
        json={"category_ids": [c2]},
        headers=admin_headers,
    )
    assert response.status_code == 200
    names = [c["name"] for c in response.json()["categories"]]
    assert names == ["Gaming"]


async def test_deleting_category_keeps_products(client, admin_headers):
    cat_id = await create_category(client, admin_headers, "Electronics")
    created = (
        await client.post(
            "/api/v1/products",
            json={"name": "Mouse", "price": "10.00", "stock": 5, "category_ids": [cat_id]},
            headers=admin_headers,
        )
    ).json()

    await client.delete(f"/api/v1/categories/{cat_id}", headers=admin_headers)

    product = (await client.get(f"/api/v1/products/{created['id']}")).json()
    assert product["name"] == "Mouse"   # product survived
    assert product["categories"] == []  # the link vanished