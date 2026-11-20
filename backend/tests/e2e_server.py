"""Máy chủ CHỈ DÀNH CHO KIỂM THỬ frontend/backend cục bộ, giả lập xác thực."""
import os

if (os.getenv("TEST_ONLY_AUTH_STUB") != "1" or not os.getenv("TEST_DATABASE_URL")
        or os.getenv("TEST_DATABASE_URL") != os.getenv("DATABASE_URL")):
    raise RuntimeError("Chỉ chạy trong môi trường kiểm thử cục bộ")

from app.auth import current_subject
from app.main import app

app.dependency_overrides[current_subject] = lambda: "integration-test-subject"
