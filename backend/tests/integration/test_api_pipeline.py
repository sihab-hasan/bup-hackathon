def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_optimize_energy_returns_expected_schema(client, valid_payload):
    response = client.post("/optimize-energy", json=valid_payload)

    assert response.status_code == 200
    body = response.json()
    assert body["scenario_id"] == "integration-case"
    assert len(body["directive_interpretation"]) == 1
    assert body["directive_interpretation"][0]["explanation"]
    assert len(body["hourly_plan"]) == 24
    assert body["total_grid_kwh"] == 516.0
    assert body["total_cost_bdt"] == 2580.0
    assert body["peak_grid_kwh"] == 33.0


def test_rejects_missing_hour(client, valid_payload):
    valid_payload["hours"].pop()

    response = client.post("/optimize-energy", json=valid_payload)

    assert response.status_code == 422


def test_rejects_duplicate_hour(client, valid_payload):
    valid_payload["hours"][23]["hour"] = 22

    response = client.post("/optimize-energy", json=valid_payload)

    assert response.status_code == 422


def test_rejects_blank_operator_note(client, valid_payload):
    valid_payload["operator_notes"] = ["  "]

    response = client.post("/optimize-energy", json=valid_payload)

    assert response.status_code == 422


def test_rejects_more_than_three_notes(client, valid_payload):
    valid_payload["operator_notes"] = ["a", "b", "c", "d"]

    response = client.post("/optimize-energy", json=valid_payload)

    assert response.status_code == 422


def test_rejects_invalid_battery_bounds(client, valid_payload):
    valid_payload["battery"]["initial_energy_kwh"] = 60

    response = client.post("/optimize-energy", json=valid_payload)

    assert response.status_code == 422
