import httpx
import asyncio
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from shared.schemas import HeartbeatRequest, MatchRequest, NodeRegistration
from coordinator.registry import registry

app = FastAPI(title="Rare Disease Coordinator")
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
SECURE_HEADERS = {
    "X-API-Key": "SUPER_SECURE_RARE_DISEASE_NETWORK_KEY_2026",
    "X-Role": "admin"
}

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

@app.get("/dashboard", include_in_schema=False)
def dashboard():
    return FileResponse(FRONTEND_DIR / "index.html")

@app.get("/")
def health_check():
    nodes = registry.get_active_node_details()
    active_count = sum(1 for node in nodes if node["status"] == "online")
    return {"status": "Coordinator is running", "active_nodes": active_count, "nodes": nodes}

@app.get("/nodes")
def list_nodes():
    nodes = registry.get_active_node_details()
    return {
        "total": len(nodes),
        "active": sum(1 for node in nodes if node["status"] == "online"),
        "nodes": nodes,
    }

@app.post("/register")
def register_node(data: NodeRegistration):
    registry.register_node(data.node_id, data.url, data.hospital_name, data.records, data.symptoms)
    return {"status": "Registered successfully"}

@app.post("/heartbeat")
def heartbeat(data: HeartbeatRequest):
    if registry.heartbeat(data.node_id, data.records, data.symptoms, data.hospital_name):
        return {"status": "Alive"}
    return {"status": "Unknown Node", "action": "Please Re-register"}

@app.get("/symptoms")
async def network_symptoms():
    """Aggregate symptom metadata from every online hospital node."""
    active_map = registry.get_active_node_map()
    symptoms = {}
    async with httpx.AsyncClient() as client:
        for url, node in active_map.items():
            try:
                response = await client.get(f"{url}/symptoms", timeout=4.0)
                if response.status_code != 200:
                    continue
                for symptom in response.json().get("symptoms", []):
                    key = symptom["name"].strip().lower()
                    entry = symptoms.setdefault(
                        key,
                        {
                            "id": symptom.get("id"),
                            "name": symptom["name"],
                            "snomed_code": symptom.get("snomed_code"),
                            "sources": [],
                        },
                    )
                    entry["sources"].append(node["node_id"])
            except Exception:
                continue
    return {"total": len(symptoms), "symptoms": sorted(symptoms.values(), key=lambda item: item["name"])}

@app.post("/find-matches")
async def broadcast_search(request: MatchRequest):
    all_matches = []
    active_nodes = registry.get_active_node_map()
    active_urls = list(active_nodes.keys())
    
    if not active_urls:
        return {"total_matches_found": 0, "message": "No active hospital nodes available.", "results": []}
    
    payload = request.model_dump() if hasattr(request, "model_dump") else request.dict()

    async def fetch_from_node(client, url):
        try:
            # 5 second timeout per node, with secure headers
            response = await client.post(
                f"{url}/search", 
                json=payload, 
                headers=SECURE_HEADERS,
                timeout=5.0
            )
            if response.status_code == 200:
                data = response.json()
                if "results" in data:
                    return data["results"]
            else:
                print(f"Node {url} Access Denied: {response.text}")
        except Exception as e:
            print(f"Node {url} failed: {e}")
        return []

    # Parallel distributed querying
    async with httpx.AsyncClient() as client:
        tasks = [fetch_from_node(client, url) for url in active_urls]
        results = await asyncio.gather(*tasks)
        
        for url, res in zip(active_urls, results):
            if res:
                node = active_nodes[url]
                for match in res:
                    match["node_id"] = node["node_id"]
                    match["node_name"] = node.get("hospital_name")
                    all_matches.append(match)
                
    # Keep the strongest representative for each disease while preserving node source details.
    best_by_disease = {}
    for match in all_matches:
        key = match.get("disease_name") or match.get("record_id")
        if key not in best_by_disease or match.get("similarity_score", 0) > best_by_disease[key].get("similarity_score", 0):
            best_by_disease[key] = match
    ranked_matches = sorted(best_by_disease.values(), key=lambda x: x.get("similarity_score", 0), reverse=True)
    return {
        "total_matches_found": len(ranked_matches),
        "queried_nodes": len(active_urls),
        "results": ranked_matches[: request.top_k],
    }

@app.get("/network-summary")
async def network_summary():
    active_nodes = registry.get_active_node_details()
    summaries = []

    async with httpx.AsyncClient() as client:
        for node in active_nodes:
            if node["status"] != "online":
                summaries.append(node)
                continue
            try:
                response = await client.get(f"{node['url']}/status-summary", timeout=3.0)
                summary = response.json() if response.status_code == 200 else {}
            except Exception:
                summary = {"status": "offline"}
            summaries.append({**node, **summary})

    return {
        "active_nodes": sum(1 for item in summaries if item.get("status") == "online"),
        "total_records": sum(item.get("records", 0) for item in summaries),
        "total_audit_logs": sum(item.get("audit_logs", 0) for item in summaries),
        "nodes": summaries,
    }

@app.get("/network-analytics")
async def network_analytics():
    active_urls = registry.get_active_nodes()
    analytics = {
        "hotspots": [],
        "duplicates": [],
        "rare_patterns": [],
        "risk_alerts": [],
        "timeline": [],
    }

    endpoints = {
        "hotspots": "/analytics/hotspots",
        "duplicates": "/analytics/duplicates",
        "rare_patterns": "/analytics/rare-patterns",
        "risk_alerts": "/analytics/risk-alerts",
        "timeline": "/analytics/symptom-evolution",
    }

    async with httpx.AsyncClient() as client:
        for url in active_urls:
            for key, path in endpoints.items():
                try:
                    response = await client.get(f"{url}{path}", headers=SECURE_HEADERS, timeout=4.0)
                    if response.status_code != 200:
                        continue
                    data = response.json()
                    if key == "hotspots":
                        analytics[key].extend(data.get("hotspots", []))
                    elif key == "timeline":
                        analytics[key].extend(data.get("timeline", []))
                    else:
                        analytics[key].extend(data.get(key, data.get("patterns", data.get("alerts", []))))
                except Exception:
                    continue

    return analytics

def _first_active_url():
    active_urls = registry.get_active_nodes()
    return active_urls[0] if active_urls else None

@app.get("/audit-logs")
async def network_audit_logs(request: Request):
    logs = []
    async with httpx.AsyncClient() as client:
        for url, node in registry.get_active_node_map().items():
            try:
                response = await client.get(
                    f"{url}/audit-logs",
                    headers={
                        "X-API-Key": request.headers.get("X-API-Key", SECURE_HEADERS["X-API-Key"]),
                        "X-Role": request.headers.get("X-Role", "admin"),
                    },
                    timeout=4.0,
                )
                if response.status_code == 200:
                    for log in response.json().get("logs", []):
                        logs.append({**log, "node_id": node["node_id"], "hospital_name": node.get("hospital_name")})
            except Exception:
                continue
    logs.sort(key=lambda item: item.get("timestamp") or "", reverse=True)
    return {"total": len(logs), "logs": logs[:50]}

@app.post("/admin/diseases")
async def proxy_add_disease(payload: dict, request: Request):
    url = _first_active_url()
    if not url:
        return {"status": "error", "message": "No active hospital nodes available."}
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{url}/admin/diseases", json=payload, headers={"X-API-Key": request.headers.get("X-API-Key", ""), "X-Role": request.headers.get("X-Role", "admin")}, timeout=5.0)
    return response.json()

@app.post("/admin/symptoms")
async def proxy_add_symptom(payload: dict, request: Request):
    url = _first_active_url()
    if not url:
        return {"status": "error", "message": "No active hospital nodes available."}
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{url}/admin/symptoms", json=payload, headers={"X-API-Key": request.headers.get("X-API-Key", ""), "X-Role": request.headers.get("X-Role", "admin")}, timeout=5.0)
    return response.json()

@app.post("/admin/clinical-records")
async def proxy_add_record(payload: dict, request: Request):
    url = _first_active_url()
    if not url:
        return {"status": "error", "message": "No active hospital nodes available."}
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{url}/admin/clinical-records", json=payload, headers={"X-API-Key": request.headers.get("X-API-Key", ""), "X-Role": request.headers.get("X-Role", "admin")}, timeout=5.0)
    return response.json()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
