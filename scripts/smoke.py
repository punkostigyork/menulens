"""Read-only/filter-only smoke checks against a running stack. No paid API calls."""
import argparse
import json
from urllib.request import Request, urlopen

parser = argparse.ArgumentParser()
parser.add_argument("--frontend", default="http://localhost:3000")
parser.add_argument("--backend", default="http://localhost:8000")
args = parser.parse_args()

def request(url, data=None):
    payload = json.dumps(data).encode() if data is not None else None
    req = Request(url, data=payload, headers={"Content-Type":"application/json"} if payload else {})
    with urlopen(req, timeout=15) as response:
        assert response.status == 200, url
        return response.read()

assert json.loads(request(args.backend + "/health")) == {"status":"ok", "database":"connected"}
for path in ["/", "/upload", "/search", "/explore", "/demo"]:
    assert b"MenuLens" in request(args.frontend + path), path
request(args.backend + "/docs")
info = json.loads(request(args.frontend + "/api/demo"))
if info["menu_id"]:
    menu_id = info["menu_id"]
    menu = json.loads(request(args.frontend + "/api/menus/" + menu_id))
    assert menu["is_demo"] and menu["status"] == "processed"
    assert sum(len(s["items"]) for s in menu["sections"]) == 4
    result = json.loads(request(args.frontend + "/api/search", {"menu_id":menu_id, "filters":{"ingredients":["chicken"], "max_price":6000, "currency":"HUF"}}))
    assert [r["item"]["name"] for r in result["results"]] == ["Csirkepaprikas"]
    assert request(args.frontend + "/api/demo/source").startswith(b"%PDF-")
    print("PASS: health, PostgreSQL, pages, API proxy, seeded demo, deterministic search and PDF.")
else:
    print("PASS: health, PostgreSQL, pages and API proxy. Demo checks skipped: seed disabled or absent.")
