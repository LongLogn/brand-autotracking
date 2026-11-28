import os
import json
from functools import lru_cache
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session


def database_url():
    url = os.getenv("DATABASE_URL")
    if url:
        return make_url(url)
    secret_id = os.getenv("DATABASE_SECRET_ARN")
    host = os.getenv("DATABASE_HOST")
    name = os.getenv("DATABASE_NAME")
    if not secret_id or not host or not name:
        raise RuntimeError("Thiếu cấu hình database")
    bundle_override = os.getenv("DATABASE_SSL_ROOT_CERT")
    bundle = Path(bundle_override) if bundle_override else Path(__file__).with_name("rds-ca-bundle.pem")
    if not bundle.is_file():
        raise RuntimeError("Thiếu CA bundle để xác minh chứng chỉ RDS")
    import boto3
    secret = json.loads(boto3.client("secretsmanager").get_secret_value(SecretId=secret_id)["SecretString"])
    return URL.create("postgresql+psycopg", username=secret["username"], password=secret["password"],
                      host=host, port=5432, database=name, query={"sslmode": "verify-full", "sslrootcert": str(bundle.resolve())})


@lru_cache(maxsize=1)
def engine():
    return create_engine(database_url(), pool_pre_ping=True, pool_size=2, max_overflow=0)


def session():
    with Session(engine()) as db:
        yield db


def reserve_owner_quota(db: Session, brand_id, provider: str, day, amount: int, limit: int) -> bool:
    """Giữ chỗ trong cùng giao dịch với trần chung. Bên gọi rollback khi hết hạn mức."""
    if amount > limit:
        return False
    from app.models import Brand, OwnerProviderQuota

    owner_id = db.scalar(select(Brand.owner_id).where(Brand.id == brand_id))
    if owner_id is None:
        raise LookupError("Nhãn hàng không tồn tại")
    table = OwnerProviderQuota.__table__
    statement = insert(table).values(owner_id=owner_id, provider=provider, day=day, reserved=amount)
    statement = statement.on_conflict_do_update(
        index_elements=[table.c.owner_id, table.c.provider, table.c.day],
        set_={"reserved": table.c.reserved + amount},
        where=table.c.reserved + amount <= limit,
    ).returning(table.c.reserved)
    return db.scalar(statement) is not None
