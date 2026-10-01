"""Full ingestion against real Gemini + Supabase. Run with:  python -m pytest -m live"""
import pytest
from fastapi.testclient import TestClient

from app.db import get_supabase
from app.main import app

pytestmark = pytest.mark.live


def test_upload_real_pdf_end_to_end(make_pdf):
    client = TestClient(app)
    pdf = make_pdf(["Cats are small domesticated animals.", "The project codename is BLUEHERON."])
    r = client.post("/upload", files={"file": ("live.pdf", pdf, "application/pdf")})
    assert r.status_code == 200, r.text
    doc_id = r.json()["doc_id"]
    try:
        rows = get_supabase().table("chunks").select("page,content").eq("doc_id", doc_id).execute().data
        assert len(rows) == r.json()["chunks"] == 2
        assert sorted(row["page"] for row in rows) == [1, 2]
    finally:
        assert client.delete(f"/documents/{doc_id}").status_code == 200
