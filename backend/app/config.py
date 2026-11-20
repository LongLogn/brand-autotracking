"""Cấu hình bảo vệ biên giữa frontend và backend."""
from urllib.parse import urlsplit


def cors_origins(value: str) -> list[str]:
    result = []
    for origin in (part.strip() for part in value.split(",")):
        if not origin:
            continue
        try:
            parsed = urlsplit(origin)
            host, port = parsed.hostname, parsed.port
        except ValueError:
            raise ValueError("CORS_ORIGINS không hợp lệ") from None
        is_local = host in {"localhost", "127.0.0.1", "::1"}
        if (not host or "*" in origin or parsed.username or parsed.password or parsed.path
                or parsed.query or parsed.fragment or port == 0
                or not (parsed.scheme == "https" or (parsed.scheme == "http" and is_local))):
            raise ValueError("CORS_ORIGINS không hợp lệ")
        result.append(origin)
    return list(dict.fromkeys(result))
