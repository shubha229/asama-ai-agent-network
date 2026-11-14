import json
import os

import httpx

API = os.getenv("API_BASE", "http://127.0.0.1:8000")
RUNNER = "http://127.0.0.1:9000"

AGENTS = {
    "swiggy": {
        "agent_name": "Swiggy Offers Agent", "company_name": "Swiggy",
        "industry": "Food Delivery",
        "description": "Swiggy runs food and grocery delivery and restaurant partnerships across India.",
        "interests": ["food delivery offers", "restaurant partnerships", "festival discounts", "delivery payment partnerships"],
    },
    "phonepe": {
        "agent_name": "PhonePe Partnerships Agent", "company_name": "PhonePe",
        "industry": "Payments and Fintech",
        "description": "PhonePe is a digital payments company offering UPI payments, wallets and merchant payment solutions.",
        "interests": ["UPI payments", "cashback offers", "merchant payment partnerships", "e-commerce and food delivery payment offers", "festive season promotions"],
    },
    "hdfc": {
        "agent_name": "HDFC Bank Cards Agent", "company_name": "HDFC Bank",
        "industry": "Banking",
        "description": "HDFC Bank provides credit cards, debit cards and retail banking products.",
        "interests": ["credit card offers", "debit card cashback", "merchant tie-ups for card payments", "festive season card discounts", "e-commerce and food delivery card partnerships"],
    },
    "bajaj": {
        "agent_name": "Bajaj Auto Sales Agent", "company_name": "Bajaj Auto",
        "industry": "Automobile",
        "description": "Bajaj Auto manufactures motorcycles, scooters and electric vehicles sold through a dealer network.",
        "interests": ["motorcycles", "electric scooters", "dealership network", "vehicle launches"],
    },
}


def main():
    keys = {}
    for short, data in AGENTS.items():
        body = dict(data)
        body["webhook_url"] = f"{RUNNER}/webhook/{short}"
        r = httpx.post(f"{API}/api/v1/agents/register", json=body, timeout=180)
        if r.status_code != 201:
            print(f"FAILED for {short}: {r.status_code} {r.text}")
            print("If it says already registered, run: python reset_db.py")
            return
        res = r.json()
        keys[short] = {
            "agent_id": res["agent"]["id"],
            "api_key": res["api_key"],
            "webhook_secret": res["webhook_secret"],
            "agent_name": data["agent_name"],
            "company_name": data["company_name"],
            "industry": data["industry"],
            "description": data["description"],
        }
        print("Registered:", short)

    path = os.path.join(os.path.dirname(__file__), "keys.json")
    with open(path, "w") as f:
        json.dump(keys, f, indent=2)
    print("Saved keys to", path)


if __name__ == "__main__":
    main()