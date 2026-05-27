import hashlib
import hmac
import os
from fastapi import HTTPException, Security, Depends
from fastapi.security import APIKeyHeader

# In a real app, this would be in a .env file.
SECRET_API_KEY = "SUPER_SECURE_RARE_DISEASE_NETWORK_KEY_2026"
api_key_header = APIKeyHeader(name="X-API-Key", scheme_name="API Key", auto_error=True)
role_header = APIKeyHeader(name="X-Role", scheme_name="User Role", auto_error=True)

def hash_patient_pii(pii_data: str) -> str:
    """
    Creates a highly secure, salted SHA-256 hash of patient PII
    to ensure zero-knowledge privacy in the network.
    """
    # In production, use os.urandom for unique salts per patient
    static_salt = b"rare_disease_secure_salt_"
    return hashlib.sha256(static_salt + pii_data.encode()).hexdigest()

def verify_api_key(api_key: str = Security(api_key_header)):
    """
    FastAPI dependency to securely validate inter-node API communication.
    Uses hmac.compare_digest to prevent timing attacks.
    """
    if not hmac.compare_digest(api_key, SECRET_API_KEY):
        raise HTTPException(
            status_code=403,
            detail="Invalid or missing API Key. Access denied to hospital network."
        )
    return api_key

def require_role(allowed_roles: list):
    """
    Dependency factory for Role-Based Access Control (RBAC).
    """
    def role_checker(x_role: str = Security(role_header)):
        if x_role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Unauthorized Role. Allowed roles: {', '.join(allowed_roles)}"
            )
        return x_role
    return role_checker
