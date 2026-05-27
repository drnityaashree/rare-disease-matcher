import requests
from fastapi.testclient import TestClient

from coordinator.main import app as coordinator_app
from node.core.crypto import SECRET_API_KEY
from node.main import app as node_app
from shared.seed_data import seed_database


HEADERS = {
    "X-API-Key": SECRET_API_KEY,
    "X-Role": "admin",
}


def check(name, condition):
    status = "PASS" if condition else "FAIL"
    print(f"{status}: {name}")
    if not condition:
        raise AssertionError(name)


def run_local_api_tests():
    seed_database()
    node = TestClient(node_app)
    coordinator = TestClient(coordinator_app)

    health = node.get("/")
    check("node health", health.status_code == 200)

    symptoms = node.get("/symptoms")
    check("symptoms loaded", symptoms.status_code == 200 and symptoms.json()["total"] >= 10)

    search = node.post(
        "/search",
        json={
            "symptoms": ["high temperature", "seizures", "small head"],
            "severity": {"fever": 5, "seizures": 5, "microcephaly": 5},
            "notes": "infant case with neurological symptoms",
            "top_k": 3,
        },
        headers=HEADERS,
    )
    body = search.json()
    check("node ML search", search.status_code == 200 and body["results"])
    check("zika top result", body["results"][0]["disease_name"] == "Congenital Zika Syndrome")
    check("risk alert generated", body["results"][0]["risk_alert"] in {"HIGH", "CRITICAL"})

    protected = node.get("/cases")
    check("security rejects missing key", protected.status_code in {401, 403})

    analytics = node.get("/analytics/risk-alerts", headers=HEADERS)
    check("risk analytics", analytics.status_code == 200)

    coordinator_health = coordinator.get("/")
    check("coordinator health", coordinator_health.status_code == 200)


def run_live_distributed_test():
    try:
        nodes = requests.get("http://127.0.0.1:8000/nodes", timeout=2).json()
        response = requests.post(
            "http://127.0.0.1:8000/find-matches",
            json={"symptoms": ["high temperature", "seizures", "small head"], "top_k": 3},
            timeout=5,
        )
    except requests.RequestException:
        print("SKIP: live distributed test, servers are not running")
        return

    check("live node registration", nodes.get("total", 0) >= 1)
    data = response.json()
    check("live distributed search", response.status_code == 200 and data.get("queried_nodes", 0) >= 1)


if __name__ == "__main__":
    run_local_api_tests()
    run_live_distributed_test()
    print("All integration checks completed.")
