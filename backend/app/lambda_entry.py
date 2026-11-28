"""Entrypoint API và migration; migration chỉ gọi qua IAM, không công khai HTTP."""
import json
import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from mangum import Mangum
from psycopg import sql
from sqlalchemy import create_engine

from app.database import database_url

from app.main import app

handler = Mangum(app, lifespan="off")


def provision_runtime_login(admin_engine, password: str) -> None:
    """Cấp quyền cho login riêng trên database ứng dụng, sau khi schema đã được nâng."""
    with admin_engine.begin() as connection:
        raw = connection.connection.driver_connection
        with raw.cursor() as cursor:
            cursor.execute("SELECT current_user, current_database()")
            administrator, database = cursor.fetchone()
            if administrator == "brand_runtime":
                raise ValueError("Migration phải dùng tài khoản riêng")
            cursor.execute("SELECT pg_advisory_xact_lock(638447212)")
            cursor.execute("""
                SELECT rolcanlogin AND NOT (rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls)
                    AND NOT EXISTS (SELECT 1 FROM pg_auth_members WHERE member = role.oid)
                FROM pg_roles AS role WHERE rolname = 'brand_runtime'
            """)
            existing = cursor.fetchone()
            if existing is not None and not existing[0]:
                raise ValueError("Vai trò brand_runtime hiện có quyền vượt phạm vi ứng dụng")
            # Tạo verifier ở client để mật khẩu gốc không nằm trong câu SQL.
            verifier = raw.pgconn.encrypt_password(password.encode(), b"brand_runtime", b"scram-sha-256").decode()
            command = sql.SQL("CREATE ROLE" if existing is None else "ALTER ROLE")
            cursor.execute(command + sql.SQL(
                " brand_runtime LOGIN PASSWORD {}"
            ).format(sql.Literal(verifier)))

            cursor.execute(sql.SQL("REVOKE CREATE, TEMPORARY ON DATABASE {} FROM PUBLIC").format(sql.Identifier(database)))
            cursor.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO brand_runtime").format(sql.Identifier(database)))
            cursor.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
            cursor.execute("GRANT USAGE ON SCHEMA public TO brand_runtime")
            cursor.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO brand_runtime")
            cursor.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO brand_runtime")
            cursor.execute("REVOKE ALL ON TABLE public.alembic_version FROM brand_runtime")
            cursor.execute(
                "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO brand_runtime"
            )
            cursor.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO brand_runtime")


def migrate(event, context):
    root = Path(__file__).resolve().parent.parent
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    command.upgrade(config, "head")
    runtime_secret = os.getenv("RUNTIME_DATABASE_SECRET_ARN")
    if runtime_secret:
        if runtime_secret == os.getenv("DATABASE_SECRET_ARN"):
            raise ValueError("Secret runtime và migration phải khác nhau")
        import boto3

        credentials = json.loads(boto3.client("secretsmanager").get_secret_value(SecretId=runtime_secret)["SecretString"])
        if credentials.get("username") != "brand_runtime" or not credentials.get("password"):
            raise ValueError("Secret runtime phải chứa thông tin của brand_runtime")
        admin_engine = create_engine(database_url(), hide_parameters=True)
        try:
            provision_runtime_login(admin_engine, credentials["password"])
        finally:
            admin_engine.dispose()
    return {"status": "ok"}
