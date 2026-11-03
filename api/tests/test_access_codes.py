"""
Integration tests for access-code generation and enforcement on session start.
Exercise the full stack against the PostgreSQL test database.
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

MC = {"type": "multiple_choice",
      "options": [{"id": "a", "text": "Paris"}, {"id": "b", "text": "London"}],
      "correct_answer": "a", "points": 1}


async def _auth(token):
    return {"Authorization": f"Bearer {token}"}


async def _make_code_test(client: AsyncClient, token: str) -> dict:
    q = (await client.post("/api/v1/questions", json={**MC, "prompt": "Capital?"}, headers=await _auth(token))).json()
    resp = await client.post("/api/v1/tests", json={
        "title": "Gated", "access": "code",
        "blocks": [{"title": None, "context_json": None, "order": 0,
                    "questions": [{"question_id": q["id"], "order": 0}]}],
    }, headers=await _auth(token))
    test_id = resp.json()["id"]
    return (await client.post(f"/api/v1/tests/{test_id}/publish", headers=await _auth(token))).json()


async def test_generate_and_list_codes(client: AsyncClient, admin_token: str):
    test = await _make_code_test(client, admin_token)
    resp = await client.post(f"/api/v1/tests/{test['id']}/access-codes",
                             json={"count": 5, "max_uses": 1, "prefix": "CLASS-"},
                             headers=await _auth(admin_token))
    assert resp.status_code == 201, resp.text
    codes = resp.json()
    assert len(codes) == 5
    assert all(c["code"].startswith("CLASS-") for c in codes)
    assert all(c["remaining"] == 1 for c in codes)

    listed = (await client.get(f"/api/v1/tests/{test['id']}/access-codes", headers=await _auth(admin_token))).json()
    assert len(listed) == 5


async def test_code_required_and_enforced(client: AsyncClient, admin_token: str):
    test = await _make_code_test(client, admin_token)
    code = (await client.post(f"/api/v1/tests/{test['id']}/access-codes",
                              json={"count": 1, "max_uses": 1},
                              headers=await _auth(admin_token))).json()[0]["code"]

    # No code → 403
    r = await client.post(f"/api/v1/sessions/take/{test['link_token']}", json={})
    assert r.status_code == 403

    # Wrong code → 403
    r = await client.post(f"/api/v1/sessions/take/{test['link_token']}", json={"access_code": "NOPE99"})
    assert r.status_code == 403

    # Valid code (lower-case, matched case-insensitively) → 201
    r = await client.post(f"/api/v1/sessions/take/{test['link_token']}", json={"access_code": code.lower()})
    assert r.status_code == 201, r.text

    # Single-use code exhausted → 403
    r = await client.post(f"/api/v1/sessions/take/{test['link_token']}", json={"access_code": code})
    assert r.status_code == 403


async def test_revoked_code_rejected(client: AsyncClient, admin_token: str):
    test = await _make_code_test(client, admin_token)
    created = (await client.post(f"/api/v1/tests/{test['id']}/access-codes",
                                 json={"count": 1}, headers=await _auth(admin_token))).json()[0]

    rev = await client.delete(f"/api/v1/tests/{test['id']}/access-codes/{created['id']}", headers=await _auth(admin_token))
    assert rev.status_code == 204

    r = await client.post(f"/api/v1/sessions/take/{test['link_token']}", json={"access_code": created["code"]})
    assert r.status_code == 403
