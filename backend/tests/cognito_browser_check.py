"""Tạo tài khoản Cognito dùng một lần không gửi email, kiểm thử rồi xóa chính tài khoản đó."""
import os
import secrets
import subprocess
import uuid
from urllib.parse import urlsplit

import boto3
database = urlsplit(os.environ.get('TEST_DATABASE_URL', ''))
local_db = (database.hostname in {'127.0.0.1', 'localhost', '::1'} and database.path == '/brand_test'
            and os.getenv('DATABASE_URL') == os.getenv('TEST_DATABASE_URL'))
if (os.getenv('TEST_COGNITO_E2E') != '1' or (not local_db and not os.getenv('TEST_AWS_API_BASE'))
        or urlsplit(os.getenv('TEST_UI_BASE', '')).hostname not in {'localhost', '127.0.0.1'}):
    raise RuntimeError('Chỉ dùng môi trường kiểm thử cục bộ')

pool = os.environ['TEST_COGNITO_POOL']
if pool != 'ap-southeast-1_qNHPiAyzR':
    raise RuntimeError('Sai user pool thử nghiệm')
session = boto3.Session(profile_name='profile-name-logn', region_name='ap-southeast-1')
client = session.client('cognito-idp')
if os.getenv('TEST_AWS_API_BASE'):
    stack_name = os.getenv('TEST_AWS_STACK', 'brand-tracking-session-api-v2')
    stack = session.client('cloudformation').describe_stacks(StackName=stack_name)['Stacks'][0]
    outputs = {item['OutputKey']: item['OutputValue'] for item in stack.get('Outputs', [])}
    if stack['StackStatus'] not in {'CREATE_COMPLETE', 'UPDATE_COMPLETE'} or outputs.get('ApiUrl') != os.environ['TEST_AWS_API_BASE']:
        raise RuntimeError('Chỉ dùng stack API thử nghiệm của phiên này')
users = [(f"test-{uuid.uuid4().hex}@example.invalid", f"Aa1!{secrets.token_urlsafe(24)}") for _ in range(2)]
created = []
try:
    for username, password in users:
        client.admin_create_user(UserPoolId=pool, Username=username, MessageAction='SUPPRESS',
                                 UserAttributes=[{'Name': 'email', 'Value': username}, {'Name': 'email_verified', 'Value': 'true'}])
        created.append(username)
        client.admin_set_user_password(UserPoolId=pool, Username=username, Password=password, Permanent=True)
    env = {**os.environ, 'TEST_COGNITO_USERNAME': users[0][0], 'TEST_COGNITO_PASSWORD': users[0][1],
           'TEST_COGNITO_USERNAME_B': users[1][0], 'TEST_COGNITO_PASSWORD_B': users[1][1]}
    subprocess.run(['node', 'tests/cognito-browser.cjs'], cwd='../frontend', env=env, check=True)
finally:
    for username in created:
        client.admin_delete_user(UserPoolId=pool, Username=username)
