import os

import httpx
import pytest

API_URL = os.environ.get(
    "APPLICATION_API_URL",
    "http://127.0.0.1:8000",
)

PASSWORDS = {
    "alice": "AlicePass123!",
    "admin": "AdminPass123!",
}


@pytest.fixture(scope="module")
def api():
    with httpx.Client(base_url=API_URL, timeout=10.0) as client:
        yield client


def login_as(api, username):
    response = api.post(
        "/login",
        json={
            "username": username,
            "password": PASSWORDS[username],
        },
    )

    assert response.status_code == 200

    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture(scope="module")
def alice_headers(api):
    return login_as(api, "alice")


@pytest.fixture(scope="module")
def admin_headers(api):
    return login_as(api, "admin")


@pytest.fixture(scope="module")
def alice_analysis(api, alice_headers):
    response = api.post(
        "/documents/1/analysis",
        headers=alice_headers,
    )

    assert response.status_code == 200
    return response.json()


# Functional tests


def test_authenticated_user(api, alice_headers):
    response = api.get("/me", headers=alice_headers)

    assert response.status_code == 200
    assert response.json()["username"] == "alice"
    assert response.json()["role"] == "USER"


def test_missing_authentication(api):
    response = api.get("/me")

    assert response.status_code == 401


def test_list_own_documents(api, alice_headers):
    response = api.get("/documents", headers=alice_headers)

    assert response.status_code == 200
    assert len(response.json()) > 0
    assert all(document["owner_id"] == "alice" for document in response.json())


def test_normal_document_search(api, alice_headers):
    response = api.get(
        "/documents/search",
        params={"q": "Alice"},
        headers=alice_headers,
    )

    assert response.status_code == 200
    assert any(document["id"] == 1 for document in response.json())
    assert all(document["owner_id"] == "alice" for document in response.json())


def test_generate_and_retrieve_analysis(api, alice_headers, alice_analysis):
    response = api.get(
        f"/analysis-results/{alice_analysis['analysis_result_id']}",
        params={"filename": alice_analysis["result_filename"]},
        headers=alice_headers,
    )

    assert response.status_code == 200
    assert response.json()["document_id"] == 1
    assert "word_count" in response.json()["content"]


def test_admin_metadata(api, alice_headers, admin_headers):
    denied = api.get(
        "/admin/documents/metadata",
        headers=alice_headers,
    )

    assert denied.status_code == 403

    allowed = api.get(
        "/admin/documents/metadata",
        headers=admin_headers,
    )

    assert allowed.status_code == 200
    assert len(allowed.json()) >= 2
    assert all("content" not in document for document in allowed.json())


# Security regression tests
# These are intentionally expected to fail in the vulnerable version.


@pytest.mark.security
def test_cwe862_reject_other_users_document(api, alice_headers):
    response = api.get(
        "/documents/2",
        headers=alice_headers,
    )

    assert response.status_code == 403


@pytest.mark.security
def test_cwe89_search_cannot_bypass_ownership(api, alice_headers):
    response = api.get(
        "/documents/search",
        params={"q": "' OR 1=1 -- "},
        headers=alice_headers,
    )

    assert response.status_code == 200
    assert all(document["owner_id"] == "alice" for document in response.json())


@pytest.mark.security
def test_cwe22_cannot_read_outside_results(api, alice_headers, alice_analysis):
    response = api.get(
        f"/analysis-results/{alice_analysis['analysis_result_id']}",
        params={"filename": "../../database.py"},
        headers=alice_headers,
    )

    # The fixed version may reject the parameter or ignore it.
    if response.status_code == 200:
        assert "def get_connection" not in response.json()["content"]
    else:
        assert response.status_code in (400, 403, 404, 422)


@pytest.mark.security
def test_composition_reject_other_users_analysis(api, alice_headers):
    response = api.post(
        "/documents/2/analysis",
        headers=alice_headers,
    )

    assert response.status_code == 403
