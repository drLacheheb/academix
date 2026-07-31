from fastapi import Request
from slowapi import Limiter


def get_client_identifier(request: Request) -> str:
    # Use Bearer token or client IP if token not present
    auth = request.headers.get("Authorization")
    if auth:
        return auth
    return request.client.host if request.client else "unknown"


limiter = Limiter(key_func=get_client_identifier)
