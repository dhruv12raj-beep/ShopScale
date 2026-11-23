USER = {"email": "alice@example.com", "password": "supersecret123"}


async def register(client):
    await client.post("/api/v1/auth/register", json=USER)


async def login(client, password="supersecret123"):
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": USER["email"], "password": password},
    )
    return response


async def test_register(client):
    response = await client.post("/api/v1/auth/register", json=USER)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "alice@example.com"
    assert "password" not in data
    assert "hashed_password" not in data


async def test_register_duplicate_email(client):
    await register(client)
    response = await client.post("/api/v1/auth/register", json=USER)
    assert response.status_code == 409


async def test_register_weak_password(client):
    response = await client.post(
        "/api/v1/auth/register", json={"email": "a@b.com", "password": "short"}
    )
    assert response.status_code == 422


async def test_login(client):
    await register(client)
    response = await login(client)
    assert response.status_code == 200
    assert "access_token" in response.json()


async def test_login_wrong_password(client):
    await register(client)
    response = await login(client, password="wrongpassword")
    assert response.status_code == 401


async def test_me_with_token(client):
    await register(client)
    token = (await login(client)).json()["access_token"]
    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == "alice@example.com"


async def test_me_without_token(client):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


async def test_me_with_garbage_token(client):
    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer nonsense"}
    )
    assert response.status_code == 401