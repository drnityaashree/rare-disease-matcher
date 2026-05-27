from datetime import datetime
from typing import Dict, List

class NodeRegistry:
    def __init__(self):
        # Maps node_id -> runtime metadata reported by each hospital node.
        self.active_nodes: Dict[str, dict] = {}
        self.timeout_seconds = 35
        self.remove_after_seconds = 120
        
    def register_node(self, node_id: str, url: str, hospital_name: str | None = None, records: int = 0, symptoms: int = 0):
        now = datetime.utcnow()
        existing = self.active_nodes.get(node_id, {})
        self.active_nodes[node_id] = {
            "url": url.rstrip("/"),
            "hospital_name": hospital_name or existing.get("hospital_name") or node_id.replace("_", " ").title(),
            "records": records or existing.get("records", 0),
            "symptoms": symptoms or existing.get("symptoms", 0),
            "first_seen": existing.get("first_seen", now),
            "last_seen": now,
        }
        print(f"[REGISTRY] Node registered: {node_id} at {url}")
        
    def heartbeat(self, node_id: str, records: int = 0, symptoms: int = 0, hospital_name: str | None = None):
        if node_id in self.active_nodes:
            self.active_nodes[node_id]["last_seen"] = datetime.utcnow()
            self.active_nodes[node_id]["records"] = records or self.active_nodes[node_id].get("records", 0)
            self.active_nodes[node_id]["symptoms"] = symptoms or self.active_nodes[node_id].get("symptoms", 0)
            if hospital_name:
                self.active_nodes[node_id]["hospital_name"] = hospital_name
            return True
        return False
        
    def deregister_node(self, node_id: str):
        if node_id in self.active_nodes:
            del self.active_nodes[node_id]
            print(f"[REGISTRY] Node deregistered: {node_id}")
            
    def _items(self, include_offline=False):
        current_time = datetime.utcnow()
        items = []
        
        dead_nodes = []
        for n_id, data in self.active_nodes.items():
            age = (current_time - data["last_seen"]).total_seconds()
            if age > self.remove_after_seconds:
                dead_nodes.append(n_id)
            elif include_offline or age <= self.timeout_seconds:
                items.append((n_id, data, age <= self.timeout_seconds))

        for n_id in dead_nodes:
            print(f"[REGISTRY] Node timeout detected, removing: {n_id}")
            self.deregister_node(n_id)
            
        return items

    def get_active_nodes(self) -> List[str]:
        """Returns URLs for active nodes."""
        return [data["url"] for _, data, online in self._items() if online]

    def get_active_node_map(self) -> Dict[str, dict]:
        """Returns active node metadata keyed by URL for coordinator fan-out."""
        return {
            data["url"]: {"node_id": node_id, **data, "status": "online"}
            for node_id, data, online in self._items()
            if online
        }

    def get_active_node_details(self, include_offline: bool = True) -> List[dict]:
        """Returns safe node metadata for dashboard/API monitoring."""
        return [
            {
                "node_id": node_id,
                "url": data["url"],
                "hospital_name": data.get("hospital_name"),
                "status": "online" if online else "offline",
                "records": data.get("records", 0),
                "symptoms": data.get("symptoms", 0),
                "first_seen": data["first_seen"].isoformat() if data.get("first_seen") else None,
                "last_seen": data["last_seen"].isoformat(),
            }
            for node_id, data, online in self._items(include_offline=include_offline)
        ]

# Singleton instance for the coordinator
registry = NodeRegistry()
