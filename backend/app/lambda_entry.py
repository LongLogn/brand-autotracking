"""Entrypoint API và migration; migration chỉ gọi qua IAM, không công khai HTTP."""
from pathlib import Path

from alembic import command
from alembic.config import Config
from mangum import Mangum

from app.main import app

handler = Mangum(app, lifespan="off")


def migrate(event, context):
    root = Path(__file__).resolve().parent.parent
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    command.upgrade(config, "head")
    return {"status": "ok"}
