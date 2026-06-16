USER_ID = "11111111-1111-1111-1111-111111111111"


async def test_get_me_returns_profile(client):
    resp = await client.get(
        "/api/v1/users/me",
        headers={"X-User-Id": USER_ID, "X-User-Roles": "member"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == USER_ID
    assert body["display_name"] == "tester"


async def test_patch_preferences_updates_values(client):
    resp = await client.patch(
        "/api/v1/users/me/preferences",
        headers={"X-User-Id": USER_ID, "X-User-Roles": "member"},
        json={"email_notifs": False, "theme": "dark"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["user_id"] == USER_ID
    assert body["email_notifs"] is False
    assert body["theme"] == "dark"


async def test_missing_gateway_identity_is_rejected(client):
    resp = await client.get("/api/v1/users/me")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "MISSING_USER_CONTEXT"
