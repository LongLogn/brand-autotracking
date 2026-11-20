import assert from 'node:assert/strict';
import test from 'node:test';
import { createCognitoTokenProvider, finishCognitoLogin, logoutCognito, startCognitoLogin } from '../src/lib/cognito.ts';

const config = { domain: 'https://login.example.test', clientId: 'client', redirectUri: 'http://localhost:5173/auth/callback', scope: 'openid brand-api/access' };
const values = new Map<string, string>();
let destination = '';
Object.assign(globalThis, {
  sessionStorage: { setItem: (key: string, value: string) => values.set(key, value), getItem: (key: string) => values.get(key) ?? null,
    removeItem: (key: string) => values.delete(key) },
  window: { location: { origin: 'http://localhost:5173', assign: (url: string) => { destination = url; } } },
});

test('đăng xuất chuyển đến Cognito với URL trở về cùng origin', () => {
  logoutCognito(config);
  const url = new URL(destination);
  assert.equal(url.pathname, '/logout');
  assert.equal(url.searchParams.get('client_id'), config.clientId);
  assert.equal(url.searchParams.get('logout_uri'), 'http://localhost:5173/');
});

test('đăng ký dùng trang signup và PKCE', async () => {
  await startCognitoLogin(config, 'signup');
  const url = new URL(destination);
  assert.equal(url.pathname, '/signup');
  assert.equal(url.searchParams.get('code_challenge_method'), 'S256');
  assert.ok(url.searchParams.get('state'));
});

test('PKCE tạo state, gửi code verifier và chỉ dùng giao dịch một lần', async () => {
  values.clear();
  await startCognitoLogin(config);
  const authorization = new URL(destination);
  assert.equal(authorization.searchParams.get('code_challenge_method'), 'S256');
  assert.equal(authorization.searchParams.get('scope'), config.scope);
  const state = authorization.searchParams.get('state');
  assert.ok(state);
  let captured = '';
  const fetcher: typeof fetch = async (_url, init) => { captured = String(init?.body); return Response.json({ access_token: 'access-test', refresh_token: 'refresh-test', expires_in: 3600 }); };
  const callback = `${config.redirectUri}?code=one-time&state=${state}`;
  assert.deepEqual(await finishCognitoLogin(config, callback, fetcher), { accessToken: 'access-test', refreshToken: 'refresh-test', expiresIn: 3600 });
  assert.ok(new URLSearchParams(captured).get('code_verifier'));
  await assert.rejects(finishCognitoLogin(config, callback, fetcher));
});

test('làm mới khi gần hết hạn và gộp yêu cầu đồng thời', async () => {
  let calls = 0;
  const fetcher: typeof fetch = async (_url, init) => {
    calls++;
    assert.equal(new URLSearchParams(String(init?.body)).get('refresh_token'), 'refresh-test');
    return Response.json({ access_token: 'new-access', expires_in: 3600 });
  };
  const provider = createCognitoTokenProvider(config, { accessToken: 'old', refreshToken: 'refresh-test', expiresIn: 1 }, fetcher);
  assert.deepEqual(await Promise.all([provider(), provider()]), ['new-access', 'new-access']);
  assert.equal(await provider(), 'new-access');
  assert.equal(calls, 1);
});

test('lỗi làm mới không trả token cũ', async () => {
  const provider = createCognitoTokenProvider(config, { accessToken: 'old', refreshToken: 'r', expiresIn: 1 }, async () => new Response('', { status: 401 }));
  assert.equal(await provider(), null);
});

test('state sai và callback sai bị từ chối trước khi gửi code', async () => {
  values.clear();
  await startCognitoLogin(config);
  let called = false;
  const fetcher: typeof fetch = async () => { called = true; return Response.json({}); };
  await assert.rejects(finishCognitoLogin(config, `${config.redirectUri}?code=x&state=wrong`, fetcher));
  assert.equal(called, false);
  await assert.rejects(finishCognitoLogin(config, 'https://other.example/auth/callback?code=x&state=y', fetcher));
  assert.equal(called, false);
});
