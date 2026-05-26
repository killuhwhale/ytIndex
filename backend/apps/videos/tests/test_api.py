import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_ingest_rejects_bad_url():
    response = APIClient().post("/api/ingest/", {"input": "https://example.com/nope"}, format="json")
    assert response.status_code == 400


@pytest.mark.django_db
def test_search_requires_query():
    response = APIClient().post("/api/search/", {"query": ""}, format="json")
    assert response.status_code == 400
