"""Worker giả chỉ phục vụ kiểm thử trình duyệt trên database thử nghiệm riêng."""
import os
import sys
from uuid import UUID

if (os.getenv('TEST_ONLY_AUTH_STUB') != '1' or not os.getenv('TEST_DATABASE_URL')
        or os.getenv('DATABASE_URL') != os.getenv('TEST_DATABASE_URL')):
    raise RuntimeError('Chỉ chạy với database thử nghiệm và xác thực giả')

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from tests.test_tracking_flow import FakeProvider
from app.tracking import run_queued

url = make_url(os.environ['TEST_DATABASE_URL'])
if url.host not in {'127.0.0.1', 'localhost', '::1'} or url.database != 'brand_test':
    raise RuntimeError('Chỉ dùng database brand_test trên localhost')
engine = create_engine(url)
try:
    result = run_queued(engine, UUID(sys.argv[1]), FakeProvider())
    if result is None or result[1] != 'success':
        raise RuntimeError('Worker giả không hoàn thành phiên chờ')
finally:
    engine.dispose()
