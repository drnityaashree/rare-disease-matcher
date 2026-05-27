from fastapi.testclient import TestClient

from node.core.crypto import SECRET_API_KEY
from node.main import app
from shared.seed_data import seed_database


def main():
    seed_database()
    client = TestClient(app)
    headers = {"X-API-Key": SECRET_API_KEY, "X-Role": "admin"}

    health = client.get("/")
    print("Health:", health.status_code, health.json())

    symptoms = client.get("/symptoms")
    print("Symptoms:", symptoms.status_code, symptoms.json()["total"])

    response = client.post(
        "/search",
        json={"symptoms": ["high temperature", "seizures", "small head"], "top_k": 3},
        headers=headers,
    )
    print("Search:", response.status_code)
    print(response.json())

    mild = client.post(
        "/search",
        json={"symptoms": ["fever"], "severity": {"fever": 1}, "notes": "mild fever and tiredness", "top_k": 3},
        headers=headers,
    )
    print("Mild fever search:", mild.status_code)
    print([(item["disease_name"], item["risk_alert"], item["rare_disease_probability"]) for item in mild.json()["results"]])

    neuro = client.post(
        "/search",
        json={
            "symptoms": ["seizures", "developmental regression", "vision loss"],
            "severity": {"seizures": 5, "developmental regression": 5, "vision loss": 4},
            "notes": "child with progressive neurological decline",
            "top_k": 3,
        },
        headers=headers,
    )
    print("Severe neuro search:", neuro.status_code)
    print([(item["disease_name"], item["risk_alert"], item["rare_disease_probability"]) for item in neuro.json()["results"]])


if __name__ == "__main__":
    main()
