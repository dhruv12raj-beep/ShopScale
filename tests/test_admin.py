async def register_and_login(client, email):
    await client.post(
        "/api/v1/auth/register", json={"email": email, "password": "password123"}
    )
    token = (
        await client.post(
            "/api/v1/auth/login", data={"username": email, "password": "password123"}
        )
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def test_list_users_requires_admin(client):
    response = await client.get("/api/v1/admin/users")
    assert response.status_code == 401
    headers = await register_and_login(client, "eve@example.com")
    response = await client.get("/api/v1/admin/users", headers=headers)
    assert response.status_code == 403


async def test_admin_can_list_users(client, admin_headers):
    response = await client.get("/api/v1/admin/users", headers=admin_headers)
    assert response.status_code == 200
    emails = [u["email"] for u in response.json()]
    assert "admin@example.com" in emails


async def test_admin_can_promote_user(client, admin_headers):
    await client.post(
        "/api/v1/auth/register", json={"email": "bob@example.com", "password": "password123"}
    )
    users = (await client.get("/api/v1/admin/users", headers=admin_headers)).json()
    bob = next(u for u in users if u["email"] == "bob@example.com")
    assert bob["is_admin"] is False

    response = await client.post(
        f"/api/v1/admin/users/{bob['id']}/promote", headers=admin_headers
    )
    assert response.status_code == 200
    assert response.json()["is_admin"] is True


async def test_promote_requires_admin(client):
    response = await client.post("/api/v1/admin/users/1/promote")
    assert response.status_code == 401


async def test_promote_unknown_user(client, admin_headers):
    response = await client.post(
        "/api/v1/admin/users/999/promote", headers=admin_headers
    )
    assert response.status_code == 404