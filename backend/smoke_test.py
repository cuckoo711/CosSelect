"""End-to-end smoke test using SQLite + TestClient (no external services)."""
import io
import os
import tempfile

os.environ["DATABASE_URL"] = "sqlite:///./_smoke_test.db"
os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="cosselect_")
os.environ["SECRET_KEY"] = "smoke-test-secret"

# Ensure a fresh db file
if os.path.exists("./_smoke_test.db"):
    os.remove("./_smoke_test.db")

from PIL import Image
from fastapi.testclient import TestClient

from app.main import app
from app.database import init_db

init_db()
client = TestClient(app)


def make_png_bytes(color=(200, 100, 50)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (2000, 1500), color).save(buf, format="PNG")
    return buf.getvalue()


def check(cond, label):
    print(("PASS " if cond else "FAIL ") + label)
    if not cond:
        raise SystemExit(1)


# health
r = client.get("/api/health")
check(r.json()["code"] == 0, "health")

# create space
r = client.post("/api/spaces").json()
check(r["code"] == 0, "create space")
space_id = r["data"]["space_id"]
manage_key = r["data"]["manage_key"]
invite_code = r["data"]["invite_code"]
check(isinstance(space_id, str) and not space_id.isdigit() and len(space_id) >= 8, "space_id is random string")
check(len(invite_code) == 8 and invite_code.isupper() or any(c.isdigit() for c in invite_code), "invite code format")
lead = {"X-Manage-Key": manage_key}

# enumeration protection: guessing simple ids returns 404
check(client.get("/api/spaces/1/verify", params={"code": "XXXXXXXX"}).json()["data"]["valid"] is False, "enum id 1 not valid")

# create category (leader only) - without key should fail
r = client.post(f"/api/spaces/{space_id}/categories", json={"name": "第一章"})
check(r.json()["code"] == 403, "category create denied without key")

r = client.post(f"/api/spaces/{space_id}/categories", json={"name": "第一章"}, headers=lead).json()
check(r["code"] == 0, "category create")
cat_id = r["data"]["id"]

# sub category
r = client.post(f"/api/spaces/{space_id}/categories", json={"name": "子类", "parent_id": cat_id}, headers=lead).json()
sub_id = r["data"]["id"]
check(r["code"] == 0, "sub category create")

# list categories tree
r = client.get(f"/api/spaces/{space_id}/categories", headers=lead).json()
check(r["code"] == 0 and len(r["data"]) == 1 and len(r["data"][0]["children"]) == 1, "category tree")

# upload photos
files = [("files", ("a.png", make_png_bytes((10, 20, 30)), "image/png")),
         ("files", ("b.png", make_png_bytes((90, 80, 70)), "image/png"))]
r = client.post(f"/api/spaces/{space_id}/photos/upload", data={"category_id": cat_id}, files=files, headers=lead).json()
check(r["code"] == 0 and r["data"]["count"] == 2, "upload 2 photos")
photo_ids = [p["id"] for p in r["data"]["photos"]]

# upload an oversized image (24MP) and verify it is compressed to <=5MP
big_buf = io.BytesIO()
Image.new("RGB", (6000, 4000), (12, 34, 56)).save(big_buf, format="PNG")
rb = client.post(
    f"/api/spaces/{space_id}/photos/upload",
    data={"category_id": cat_id},
    files=[("files", ("big.png", big_buf.getvalue(), "image/png"))],
    headers=lead,
).json()
big_id = rb["data"]["photos"][0]["id"]
# processing is synchronous in fallback mode (no broker); verify stored image dimensions
from app.database import SessionLocal as _SL
from app.models import Photo as _Photo
from PIL import Image as _Img
_db = _SL()
_p = _db.get(_Photo, big_id)
with _Img.open(_p.file_path) as _im:
    _px = _im.size[0] * _im.size[1]
_db.close()
check(_px <= 5_000_000, f"oversized image compressed to <=5MP ({_px}px)")
# image endpoint serves it
check(client.get(f"/api/spaces/{space_id}/photos/{big_id}/image", headers=lead).status_code == 200, "image endpoint serves compressed")

# thumbnails generated synchronously (fallback path since no broker)
r = client.get(f"/api/spaces/{space_id}/photos/{photo_ids[0]}/thumbnail", headers=lead)
check(r.status_code == 200 and len(r.content) > 0, "thumbnail served")

# non-empty category cannot be deleted
r = client.delete(f"/api/spaces/{space_id}/categories/{cat_id}", headers=lead).json()
check(r["code"] != 0, "non-empty category delete blocked")

# empty sub category can be deleted
r = client.delete(f"/api/spaces/{space_id}/categories/{sub_id}", headers=lead).json()
check(r["code"] == 0, "empty category deleted")

# verify code
r = client.get(f"/api/spaces/{space_id}/verify", params={"code": invite_code}).json()
check(r["data"]["valid"] is True, "verify code valid")

# participant join
r = client.post(f"/api/spaces/{space_id}/participants", json={"nickname": "小明"}).json()
check(r["code"] == 0 and r["data"]["is_new"] is True, "participant join new")
token = r["data"]["token"]
part = {"X-Participant-Token": token}

# same nickname -> restore
r = client.post(f"/api/spaces/{space_id}/participants", json={"nickname": "小明"}).json()
check(r["data"]["is_new"] is False, "participant nickname restore")

# second participant
r2 = client.post(f"/api/spaces/{space_id}/participants", json={"nickname": "小红"}).json()
token2 = r2["data"]["token"]
part2 = {"X-Participant-Token": token2}

# rating
r = client.post(f"/api/spaces/{space_id}/photos/{photo_ids[0]}/ratings", json={"score": 4.5}, headers=part).json()
check(r["code"] == 0 and r["data"]["avg_score"] == 4.5, "rating submit")
r = client.post(f"/api/spaces/{space_id}/photos/{photo_ids[0]}/ratings", json={"score": 3.5}, headers=part2).json()
check(r["data"]["avg_score"] == 4.0 and r["data"]["rating_count"] == 2, "rating avg over 2")

# rating modify
r = client.post(f"/api/spaces/{space_id}/photos/{photo_ids[0]}/ratings", json={"score": 5.0}, headers=part).json()
check(r["data"]["avg_score"] == 4.2 and r["data"]["rating_count"] == 2, "rating modify keeps count")

# invalid step
r = client.post(f"/api/spaces/{space_id}/photos/{photo_ids[0]}/ratings", json={"score": 4.3}, headers=part).json()
check(r["code"] == 422, "rating step validation")

# comments: leader auto pin
r = client.post(f"/api/spaces/{space_id}/photos/{photo_ids[0]}/comments", json={"content": "团长意见"}, headers=lead).json()
check(r["code"] == 0 and r["data"]["is_pinned"] and r["data"]["is_leader"], "leader comment pinned")
lead_comment_id = r["data"]["id"]

r = client.post(f"/api/spaces/{space_id}/photos/{photo_ids[0]}/comments", json={"content": "我觉得不错"}, headers=part).json()
part_comment_id = r["data"]["id"]
check(r["code"] == 0 and not r["data"]["is_pinned"], "participant comment not pinned")

# list comments: pinned first
r = client.get(f"/api/spaces/{space_id}/photos/{photo_ids[0]}/comments", headers=part2).json()
check(r["data"][0]["is_pinned"] is True, "pinned comment first")

# leader cannot delete others comment
r = client.delete(f"/api/spaces/{space_id}/comments/{part_comment_id}", headers=lead).json()
check(r["code"] == 403, "leader cannot delete participant comment")

# participant edit own
r = client.put(f"/api/spaces/{space_id}/comments/{part_comment_id}", json={"content": "改一下"}, headers=part).json()
check(r["code"] == 0 and r["data"]["content"] == "改一下", "participant edit own comment")

# like toggle
r = client.post(f"/api/spaces/{space_id}/comments/{lead_comment_id}/like", headers=part).json()
check(r["data"]["liked_by_me"] and r["data"]["likes_count"] == 1, "like add")
r = client.post(f"/api/spaces/{space_id}/comments/{lead_comment_id}/like", headers=part).json()
check(not r["data"]["liked_by_me"] and r["data"]["likes_count"] == 0, "like toggle off")

# favorite
r = client.post(f"/api/spaces/{space_id}/photos/{photo_ids[0]}/favorite", headers=part).json()
check(r["data"]["favorite"] is True, "favorite add")

# photo detail
r = client.get(f"/api/spaces/{space_id}/photos/{photo_ids[0]}", headers=part).json()
check(r["code"] == 0 and r["data"]["my_score"] == 5.0 and r["data"]["my_favorite"] is True, "photo detail personal")
check(len(r["data"]["comments"]) == 2, "photo detail comments")

# photo list sorts
r = client.get(f"/api/spaces/{space_id}/photos", params={"category_id": cat_id, "sort": "score"}, headers=part).json()
check(r["code"] == 0 and r["data"][0]["id"] == photo_ids[0], "list sort by score")

# stats + export (leader)
r = client.get(f"/api/spaces/{space_id}/stats", headers=lead).json()
check(r["code"] == 0 and len(r["data"]) == 3, "stats dashboard")
r = client.get(f"/api/spaces/{space_id}/export", headers=lead)
check(r.status_code == 200 and r.content.startswith(b"\xef\xbb\xbf"), "csv export with BOM")

# regenerate code invalidates old
old_code = invite_code
r = client.post(f"/api/spaces/{space_id}/regenerate-code", headers=lead).json()
new_code = r["data"]["invite_code"]
check(new_code != old_code, "regenerate code")
r = client.get(f"/api/spaces/{space_id}/verify", params={"code": old_code}).json()
check(r["data"]["valid"] is False, "old code invalid after regen")

# data preserved after regen: participant still has rating
r = client.get(f"/api/spaces/{space_id}/photos/{photo_ids[0]}", headers=part).json()
check(r["data"]["my_score"] == 5.0, "data preserved after regen")

print("\nALL SMOKE TESTS PASSED")
