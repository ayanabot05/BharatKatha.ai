"""VidBharat backend API tests - auth, meta, projects, media isolation, coach."""
import os
import time
import uuid
import pytest
import requests

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") if os.environ.get("REACT_APP_BACKEND_URL") else "http://localhost:8000"
API = f"{BASE}/api"

ADMIN_EMAIL = "admin@vidbharat.ai"
ADMIN_PASS = "Admin@123"


def _sess():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def admin():
    s = _sess()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=30)
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="session")
def test_user():
    s = _sess()
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    r = s.post(f"{API}/auth/register", json={"name": "T", "email": email, "password": "Pass@1234"}, timeout=30)
    assert r.status_code == 200, r.text
    return s, email


# ---------- Auth ----------
class TestAuth:
    def test_register_login_logout_flow(self):
        s = _sess()
        email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        r = s.post(f"{API}/auth/register", json={"name": "Flow", "email": email, "password": "Pass@1234"}, timeout=30)
        assert r.status_code == 200
        assert r.json()["email"] == email
        # me works
        me = s.get(f"{API}/auth/me", timeout=15)
        assert me.status_code == 200
        assert me.json()["email"] == email
        # logout
        lo = s.post(f"{API}/auth/logout", timeout=15)
        assert lo.status_code == 200
        # me now 401
        me2 = s.get(f"{API}/auth/me", timeout=15)
        assert me2.status_code == 401
        # login again
        li = s.post(f"{API}/auth/login", json={"email": email, "password": "Pass@1234"}, timeout=15)
        assert li.status_code == 200
        me3 = s.get(f"{API}/auth/me", timeout=15)
        assert me3.status_code == 200

    def test_wrong_password(self):
        s = _sess()
        r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": "wrong"}, timeout=15)
        assert r.status_code == 401

    def test_register_duplicate_email(self):
        s = _sess()
        r = s.post(f"{API}/auth/register", json={"name": "A", "email": ADMIN_EMAIL, "password": "whatever"}, timeout=15)
        assert r.status_code == 400

    def test_me_without_auth(self):
        r = requests.get(f"{API}/auth/me", timeout=15)
        assert r.status_code == 401


# ---------- Meta ----------
class TestMeta:
    def test_meta(self):
        r = requests.get(f"{API}/meta", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "voices" in d and "styles" in d and "engines" in d
        assert len(d["styles"]) >= 6


# ---------- Projects CRUD ----------
class TestProjects:
    def test_list_projects(self, admin):
        r = admin.get(f"{API}/projects", timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_admin_has_completed_project(self, admin):
        r = admin.get(f"{API}/projects", timeout=15)
        projs = r.json()
        done = [p for p in projs if p.get("render", {}).get("status") == "done"]
        if not done:
            pytest.skip("No completed admin project exists; requires a real rendered-video fixture")
        p = done[0]
        assert p.get("script") and p.get("scenes") and p.get("audio")
        assert p["render"].get("video_path")

    def test_create_get_patch_delete(self, admin):
        c = admin.post(f"{API}/projects", json={"title": "TEST_proj", "language": "te"}, timeout=15)
        assert c.status_code == 200
        pid = c.json()["id"]
        g = admin.get(f"{API}/projects/{pid}", timeout=15)
        assert g.status_code == 200 and g.json()["title"] == "TEST_proj"
        p = admin.patch(f"{API}/projects/{pid}", json={"title": "TEST_updated", "idea": "A cow"}, timeout=15)
        assert p.status_code == 200 and p.json()["title"] == "TEST_updated"
        d = admin.delete(f"{API}/projects/{pid}", timeout=15)
        assert d.status_code == 200
        g2 = admin.get(f"{API}/projects/{pid}", timeout=15)
        assert g2.status_code == 404

    def test_cross_user_isolation(self, admin, test_user):
        # Create project as test user, admin should not see it
        s, _ = test_user
        c = s.post(f"{API}/projects", json={"title": "TEST_user_proj"}, timeout=15)
        assert c.status_code == 200
        pid = c.json()["id"]
        r = admin.get(f"{API}/projects/{pid}", timeout=15)
        assert r.status_code == 404
        s.delete(f"{API}/projects/{pid}", timeout=15)


# ---------- Media isolation ----------
class TestMedia:
    def test_media_requires_auth(self, admin):
        # Grab a media path from admin's completed project
        projs = admin.get(f"{API}/projects", timeout=15).json()
        p = next((x for x in projs if x.get("render", {}).get("video_path")), None)
        if not p:
            pytest.skip("No completed admin video exists for media isolation check")
        path = p["render"]["video_path"]
        # Admin owner can fetch
        r_ok = admin.get(f"{BASE}/api/media/{path}", timeout=30)
        assert r_ok.status_code == 200
        # Unauthenticated -> 401
        r_un = requests.get(f"{BASE}/api/media/{path}", timeout=15)
        assert r_un.status_code == 401
        # Other user -> 404 (not owner)
        s2 = _sess()
        email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        s2.post(f"{API}/auth/register", json={"name": "O", "email": email, "password": "Pass@1234"}, timeout=15)
        r_other = s2.get(f"{BASE}/api/media/{path}", timeout=15)
        assert r_other.status_code in (404, 401)


# ---------- Ideas suggest ----------
class TestIdeas:
    def test_suggest_ideas(self, admin):
        r = admin.post(f"{API}/ideas/suggest", json={"language": "te", "category": "Moral stories"}, timeout=60)
        assert r.status_code == 200, r.text
        ideas = r.json().get("ideas")
        assert isinstance(ideas, list) and len(ideas) >= 3


# ---------- Coach ----------
class TestCoach:
    def test_coach_analyze(self, admin):
        body = {
            "channel_name": "TEST", "niche": "stories", "language": "te", "subscribers": 1000,
            "videos": [{"title": "V1", "views": 10000, "avg_viewed_pct": 55, "viewed_vs_swiped_pct": 60,
                        "likes": 300, "retention": [100, 80, 60, 50, 40]}]
        }
        r = admin.post(f"{API}/coach/analyze", json=body, timeout=90)
        assert r.status_code == 200, r.text
        rep = r.json().get("report")
        assert rep and ("health_score" in rep or "hypotheses" in rep or "experiments" in rep)
