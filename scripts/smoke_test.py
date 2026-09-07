"""Clean environment smoke test runner against live running Uvicorn server."""

import json
import urllib.request
import urllib.error

BASE_URL = "http://127.0.0.1:8000"

def get(path: str):
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as resp:
        return resp.status, resp.headers.get_content_type(), resp.read()

def post(path: str, data: dict):
    url = f"{BASE_URL}{path}"
    payload = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        return resp.status, resp.headers.get_content_type(), resp.read()

print("--- 1. Testing /health ---")
status, ct, body = get("/health")
print(f"Status: {status}, Content-Type: {ct}")
data = json.loads(body.decode("utf-8"))
print(json.dumps(data, indent=2))
assert data["status"] == "ok"
assert data["version"] == "1.0.0"

print("\n--- 2. Testing /ready ---")
status, ct, body = get("/ready")
print(f"Status: {status}, Content-Type: {ct}")
data = json.loads(body.decode("utf-8"))
print(json.dumps(data, indent=2))
assert data["status"] == "ready"
assert data["production_model"] == "M1_SpreadOnly"
assert data["verified_leads_count"] == 101

print("\n--- 3. Testing /api/v1/inference/model-info ---")
status, ct, body = get("/api/v1/inference/model-info")
print(f"Status: {status}, Content-Type: {ct}")
data = json.loads(body.decode("utf-8"))
print(f"Production Model: {data['production_model']['model_name']} ({data['production_model']['scientific_status']})")
print(f"Reference Baseline: {data['reference_baseline']['model_name']} ({data['reference_baseline']['scientific_status']})")

print("\n--- 4. Testing /api/v1/historical/cyclones ---")
status, ct, body = get("/api/v1/historical/cyclones")
data = json.loads(body.decode("utf-8"))
print(f"Total Cyclones: {len(data)}")
for c in data:
    print(f"  - {c['storm_name']}: {c['verified_leads_count']} verified leads, {c['contemporaneous_busts_count']} contemporaneous busts, mean error {c['mean_track_error_km']} km")

print("\n--- 5. Testing /api/v1/historical/replay/MICHAUNG ---")
status, ct, body = get("/api/v1/historical/replay/MICHAUNG")
data = json.loads(body.decode("utf-8"))
print(f"Replay Mode: {data['mode']}, Total Leads: {data['total_leads']}, MAE: {data['continuous_error_summary']['mean_track_error_km']} km")
print(f"Forecast Provenance: {data['provenance']['forecast_source']}")
print(f"Verification Provenance: {data['provenance']['verification_source']}")

print("\n--- 6. Testing /api/v1/historical/bust-atlas ---")
status, ct, body = get("/api/v1/historical/bust-atlas")
data = json.loads(body.decode("utf-8"))
print(f"Total Curated Bust Records: {len(data)}")
assert len(data) == 24

print("\n--- 7. Testing /api/v1/inference/predict (Live valid 11-member payload) ---")
members = [
    {"member_id": i, "latitude": 10.5 + 0.05 * (i - 6), "longitude": 84.2 + 0.05 * (i - 6), "central_pressure_hpa": 998.0}
    for i in range(1, 12)
]
valid_payload = {
    "forecast_source": "NCMRWF TIGGE",
    "forecast_cycle": "2023-12-01T00:00:00Z",
    "valid_time": "2023-12-02T00:00:00Z",
    "lead_hours": 24,
    "ensemble_members": members,
}
status, ct, body = post("/api/v1/inference/predict", valid_payload)
data = json.loads(body.decode("utf-8"))
print(f"Status: {data['status']}, Data Quality: {data['data_quality']}, State: {data['reliability_state']}, Bust Risk: {data['bust_risk_percent']}%, Reliability Score: {data['reliability_score']}")
print(f"Message: {data['message']}")
print(f"Provenance Processing Status: {data['provenance']['processing_status']}")

print("\n--- 8. Testing /api/v1/inference/predict (Fail-safe insufficient data) ---")
insufficient_payload = {
    "forecast_source": "NCMRWF TIGGE",
    "forecast_cycle": "2023-12-01T00:00:00Z",
    "valid_time": "2023-12-02T00:00:00Z",
    "lead_hours": 24,
    "ensemble_members": [{"member_id": 1, "latitude": 10.5, "longitude": 84.2}],
}
status, ct, body = post("/api/v1/inference/predict", insufficient_payload)
data = json.loads(body.decode("utf-8"))
print(f"Fail-Safe Quality: {data['data_quality']}, State: {data['reliability_state']}")
print(f"Risk Score: {data['bust_risk_percent']}, Reliability Score: {data['reliability_score']}")
print(f"Message: {data['message']}")
assert data["data_quality"] == "DATA INSUFFICIENT"
assert data["bust_risk_percent"] is None
assert "insufficient forecast evidence" in data["message"]

print("\n--- 9. Testing Frontend SPA Root / ---")
status, ct, body = get("/")
html = body.decode("utf-8")
print(f"Status: {status}, Content-Type: {ct}, Length: {len(html)} bytes")
assert "<div id=\"root\">" in html
assert "ForecastGuard" in html
print("SPA Root rendered successfully.")

print("\n==================================================")
print("ALL LIVE DEPLOYMENT SMOKE TESTS PASSED SUCCESSFULLY")
print("==================================================")
