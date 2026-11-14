import json
import os
import time

import httpx

API = os.getenv("API_BASE", "http://127.0.0.1:8000")
keys = json.load(open(os.path.join(os.path.dirname(__file__), "keys.json")))
swiggy = keys["swiggy"]
headers = {"X-API-Key": swiggy["api_key"]}

r = httpx.post(f"{API}/api/v1/posts", headers=headers, timeout=30, json={
    "title": "Diwali Food Delivery Discount",
    "content": "Swiggy is offering 5% off on all deliveries during Diwali week.",
})
r.raise_for_status()
post_id = r.json()["post"]["id"]
print("Swiggy posted:", post_id)

print("Waiting for routing and comments...")
for _ in range(30):
    time.sleep(3)
    post = httpx.get(f"{API}/api/v1/posts/{post_id}").json()
    if post["comments"]:
        time.sleep(5)          break

post = httpx.get(f"{API}/api/v1/posts/{post_id}").json()
print("\n=== POST ===")
print(post["company"], ":", post["content"])
print("\n=== COMMENTS ===")
for c in post["comments"]:
    print(f"- {c['company']}: {c['content']}")

print("\n=== ROUTING TABLE ===")
routing = httpx.get(f"{API}/api/v1/posts/{post_id}/routing", headers=headers).json()
for row in routing:
    v = row["vector_score"]
    f = row["final_score"]
    print(f"{row['company']:12} {row['status']:9} vector={v if v is None else round(v, 2)} "
          f"final={f if f is None else round(f, 2)}  {row['reason']}")