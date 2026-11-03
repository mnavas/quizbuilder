"""
Integration tests for registered (login-gated) test access.
"""

import uuid

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

MC = {"type": "multiple_choice",
      "options": [{"id": "a", "text": "Paris"}, {"id": "b", "text": "London"}],
      "correct_answer": "a", "points": 1}


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


async def _make_registered_test(client: AsyncClient, admin_token: str) -> dict:
    q = (await client.post("/api/v1/questions", json={**MC, "prompt": "Capital?"}, headers=_auth(admin_token))).json()
    resp = await client.post("/api/v1/tests", json={
        "title": "Login-gated", "access": "registered",
        "blocks": [{"title": None, "context_json": None, "order": 0,
                    "questions": [{"question_id": q["id"], "order": 0}]}],
    }, headers=_auth(admin_token))
    test_id = resp.json()["id"]
    return (await client.post(f"/api/v1/tests/{test_id}/publish", headers=_auth(admin_token))).json()


async def test_registered_requires_login(client: AsyncClient, admin_token: str):
    test = await _make_registered_test(client, admin_token)
    r = await client.post(f"/api/v1/sessions/take/{test['link_token']}", json={})
    assert r.status_code == 401


async def test_registered_taker_can_start_with_token(client: AsyncClient, admin_token: str):
    test = await _make_registered_test(client, admin_token)

    # Admin provisions a candidate (taker) account.
    email = f"taker-{uuid.uuid4().hex[:8]}@test.com"
    created = await client.post("/api/v1/users",
                                json={"email": email, "password": "takerpass123", "role": "candidate"},
                                headers=_auth(admin_token))
    assert created.status_code == 201, created.text

    # Taker logs in and starts the test with their own token.
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": "takerpass123"})
    assert login.status_code == 200, login.text
    taker_token = login.json()["access_token"]

    start = await client.post(f"/api/v1/sessions/take/{test['link_token']}", json={}, headers=_auth(taker_token))
    assert start.status_code == 201, start.text
