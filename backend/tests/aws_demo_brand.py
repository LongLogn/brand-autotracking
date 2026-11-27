"""Tạo thương hiệu demo qua Cognito và API trên stack kiểm thử riêng."""
import os
import secrets
import subprocess
from urllib.parse import urlsplit
from uuid import uuid4

import boto3

stack_name = os.environ.get("TEST_AWS_STACK", "")
ui_url = urlsplit(os.environ.get("TEST_UI_BASE", ""))
if (os.environ.get("TEST_DEMO_AWS") != "1" or not stack_name.startswith("brand-demo-check-api-")
        or ui_url.hostname not in {"localhost", "127.0.0.1"}):
    raise RuntimeError("Chỉ chạy với stack demo và giao diện thử cục bộ")
aws = boto3.Session(profile_name="profile-name-logn", region_name="ap-southeast-1")
stack = aws.client("cloudformation").describe_stacks(StackName=stack_name)["Stacks"][0]
outputs = {item["OutputKey"]: item["OutputValue"] for item in stack.get("Outputs", [])}
params = {item["ParameterKey"]: item["ParameterValue"] for item in stack.get("Parameters", [])}
if (outputs.get("ApiUrl") != os.environ.get("TEST_AWS_API_BASE") or
        not params.get("DatabaseHost", "").startswith("brand-demo-check-data-")):
    raise RuntimeError("API hoặc database không thuộc stack thử")
pool = "ap-southeast-1_qNHPiAyzR"
client = aws.client("cognito-idp")
username = f"demo-{uuid4().hex}@example.invalid"
password = f"Aa1!{secrets.token_urlsafe(24)}"
created = False
try:
    client.admin_create_user(UserPoolId=pool, Username=username, MessageAction="SUPPRESS",
                             UserAttributes=[{"Name": "email", "Value": username}, {"Name": "email_verified", "Value": "true"}])
    created = True
    client.admin_set_user_password(UserPoolId=pool, Username=username, Password=password, Permanent=True)
    env = {**os.environ, "TEST_COGNITO_USERNAME": username, "TEST_COGNITO_PASSWORD": password}
    subprocess.run(["node", "tests/aws-demo-brand.cjs"], cwd="../frontend", env=env, check=True)
finally:
    if created:
        client.admin_delete_user(UserPoolId=pool, Username=username)
