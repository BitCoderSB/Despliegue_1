from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    j = r.json()
    assert j["ok"] is True
    assert "mode" in j

def test_daily_ok():
    params = dict(lat=19.04, lon=-98.2, start="2023-01-01", end="2023-01-10", varname="Tmax_C")
    r = client.get("/nasa/daily", params=params)
    assert r.status_code == 200
    j = r.json()
    assert j["name"] == "Tmax_C"
    assert len(j["index"]) == len(j["values"]) == 10

def test_daily_bad_varname():
    params = dict(lat=19.04, lon=-98.2, start="2023-01-01", end="2023-01-10", varname="foo")
    r = client.get("/nasa/daily", params=params)
    assert r.status_code == 400

def test_daily_bad_dates():
    params = dict(lat=19.04, lon=-98.2, start="2023-01-10", end="2023-01-01", varname="Tmax_C")
    r = client.get("/nasa/daily", params=params)
    assert r.status_code == 400

def test_probabilities_mock():
    body = {
        "lat": 19.04, "lon": -98.2, "buffer_km": 25,
        "start_date": "2015-01-01", "end_date": "2024-12-31",
        "date_of_interest": "2024-05-15", "engine": "logistic", "window_days": 7,
        "thresholds": {
            "very_hot_Tmax_C": 32, "very_cold_Tmin_C": 0,
            "very_windy_speed_ms": 10, "very_wet_precip_mmday": 20, "very_uncomfortable_HI_C": 32
        }
    }
    r = client.post("/api/probabilities", json=body)
    assert r.status_code == 200
    j = r.json()
    assert "snapshot" in j and "curves" in j and "meta" in j
