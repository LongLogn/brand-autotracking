"""Entrypoint ASGI cho EC2 sau ALB/CloudFront: `uvicorn app.server:app`.

CloudFront chuyển `/api/*` đến ALB; khi `API_PATH_PREFIX=/api`, tiền tố được bỏ để
dùng lại nguyên route FastAPI. Health check của ALB gọi thẳng `/health`.
"""
import os

from app.analysis_queue import start_background_worker
from app.main import app as api

PREFIX = os.environ.get("API_PATH_PREFIX", "").rstrip("/")
# Mỗi tiến trình uvicorn có một luồng xử lý hàng đợi phân tích AI (khi phân tích được bật).
start_background_worker()


async def app(scope, receive, send):
    if PREFIX and scope["type"] in ("http", "websocket"):
        path = scope.get("path", "")
        if path == PREFIX or path.startswith(PREFIX + "/"):
            stripped = path[len(PREFIX):] or "/"
            scope = {**scope, "path": stripped, "raw_path": stripped.encode()}
    await api(scope, receive, send)
