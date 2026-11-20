import os
import json
from functools import lru_cache

from sqlalchemy import create_engine
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
    import boto3
    secret = json.loads(boto3.client("secretsmanager").get_secret_value(SecretId=secret_id)["SecretString"])
    return URL.create("postgresql+psycopg", username=secret["username"], password=secret["password"],
                      host=host, port=5432, database=name, query={"sslmode": "require"})


@lru_cache(maxsize=1)
def engine():
    return create_engine(database_url(), pool_pre_ping=True, pool_size=2, max_overflow=0)


def session():
    with Session(engine()) as db:
        yield db
