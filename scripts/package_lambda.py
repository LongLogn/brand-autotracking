"""Đóng gói backend Linux x86_64/Python 3.12 để triển khai Lambda thử nghiệm."""
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile
from urllib.request import urlopen
from zipfile import ZIP_DEFLATED, ZipFile

RDS_CA_BUNDLE_URL = "https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem"
MAX_CA_BUNDLE_BYTES = 1024 * 1024


def read_ca_bundle(path):
    if path is None:
        with urlopen(RDS_CA_BUNDLE_URL, timeout=10) as response:
            bundle = response.read(MAX_CA_BUNDLE_BYTES + 1)
    else:
        with path.open("rb") as source:
            bundle = source.read(MAX_CA_BUNDLE_BYTES + 1)
    if len(bundle) > MAX_CA_BUNDLE_BYTES or not bundle.lstrip().startswith(b"-----BEGIN CERTIFICATE-----"):
        raise ValueError("CA bundle RDS cần có định dạng PEM hợp lệ")
    return bundle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="Đường dẫn tệp ZIP đầu ra")
    parser.add_argument("--rds-ca-bundle", type=Path, help="Tệp PEM RDS chính thức để đóng gói lại cùng phiên bản")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    backend = root / "backend"
    output = args.output.resolve()
    if output.exists():
        parser.error("Tệp đầu ra đã tồn tại")
    bundle = read_ca_bundle(args.rds_ca_bundle)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="brand-lambda-") as temp:
        deps = Path(temp)
        subprocess.run([sys.executable, "-m", "pip", "install", "--target", str(deps),
                        "--platform", "manylinux2014_x86_64", "--python-version", "3.12",
                        "--implementation", "cp", "--abi", "cp312", "--only-binary=:all:",
                        "-r", str(backend / "requirements.txt")], check=True)
        created = False
        try:
            with output.open("xb") as target:
                created = True
                with ZipFile(target, "w", ZIP_DEFLATED) as archive:
                    for file in deps.rglob("*"):
                        if file.is_file() and "__pycache__" not in file.parts and file.suffix != ".pyc":
                            archive.write(file, file.relative_to(deps).as_posix())
                    for folder in ("app", "migrations"):
                        for file in (backend / folder).rglob("*"):
                            if file.is_file() and "__pycache__" not in file.parts and file.suffix != ".pyc":
                                archive.write(file, file.relative_to(backend).as_posix())
                    archive.write(backend / "alembic.ini", "alembic.ini")
                    archive.writestr("app/rds-ca-bundle.pem", bundle)
        except Exception:
            if created:
                output.unlink(missing_ok=True)
            raise
    print(f"Lambda package: {output}")


if __name__ == "__main__":
    main()
