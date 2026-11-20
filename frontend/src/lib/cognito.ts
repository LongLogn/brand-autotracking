/** OAuth code + PKCE cho public client; không lưu access/refresh token vào storage. */
export interface CognitoConfig { domain: string; clientId: string; redirectUri: string; scope: string }
export interface CognitoTokens { accessToken: string; refreshToken: string; expiresIn: number }
const transactionKey = 'brand-tracking-oauth-transaction';

function randomString() {
  const bytes = crypto.getRandomValues(new Uint8Array(32));
  return base64url(bytes);
}
function base64url(bytes: Uint8Array) {
  return btoa(String.fromCharCode(...bytes)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}
function domainUrl(config: CognitoConfig) {
  const domain = new URL(config.domain);
  if (domain.protocol !== 'https:' || domain.username || domain.password || domain.pathname !== '/' || domain.search || domain.hash) {
    throw new Error('Cấu hình Cognito không hợp lệ');
  }
  return domain;
}

export async function startCognitoLogin(config: CognitoConfig, mode: 'login' | 'signup' = 'login') {
  const domain = domainUrl(config);
  const redirect = new URL(config.redirectUri);
  if (redirect.origin !== window.location.origin) throw new Error('Địa chỉ callback không khớp ứng dụng');
  const verifier = randomString();
  const state = randomString();
  const challenge = base64url(new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier))));
  sessionStorage.setItem(transactionKey, JSON.stringify({ verifier, state, createdAt: Date.now() }));
  const url = new URL(mode === 'signup' ? '/signup' : '/oauth2/authorize', domain);
  url.search = new URLSearchParams({ response_type: 'code', client_id: config.clientId, redirect_uri: redirect.href,
    scope: config.scope, state, code_challenge_method: 'S256', code_challenge: challenge }).toString();
  window.location.assign(url.href);
}

/** Kết thúc cookie managed login; token đã cấp vẫn tồn tại đến khi hết hạn hoặc bị thu hồi. */
export function logoutCognito(config: CognitoConfig) {
  const url = new URL('/logout', domainUrl(config));
  url.search = new URLSearchParams({ client_id: config.clientId, logout_uri: `${window.location.origin}/` }).toString();
  sessionStorage.removeItem(transactionKey);
  window.location.assign(url.href);
}

export async function finishCognitoLogin(config: CognitoConfig, callbackUrl: string, fetcher: typeof fetch = fetch) {
  const domain = domainUrl(config);
  const url = new URL(callbackUrl);
  if (url.origin + url.pathname !== new URL(config.redirectUri).origin + new URL(config.redirectUri).pathname) throw new Error('Callback không hợp lệ');
  const raw = sessionStorage.getItem(transactionKey);
  sessionStorage.removeItem(transactionKey);
  let transaction: { state?: unknown; verifier?: unknown; createdAt?: unknown };
  try { transaction = JSON.parse(raw ?? 'null') ?? {}; } catch { throw new Error('Phiên đăng nhập không hợp lệ'); }
  const state = url.searchParams.get('state');
  const code = url.searchParams.get('code');
  if (!state || state !== transaction.state || typeof transaction.verifier !== 'string' ||
      typeof transaction.createdAt !== 'number' || Date.now() - transaction.createdAt > 10 * 60_000 ||
      Date.now() < transaction.createdAt || !code || url.searchParams.has('error')) {
    throw new Error('Phiên đăng nhập không hợp lệ hoặc đã hết hạn');
  }
  const body = new URLSearchParams({ grant_type: 'authorization_code', client_id: config.clientId,
    code, redirect_uri: config.redirectUri, code_verifier: transaction.verifier });
  const response = await fetcher(new URL('/oauth2/token', domain), {
    method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body, credentials: 'omit', redirect: 'error',
  });
  if (!response.ok) throw new Error('Không đổi được mã đăng nhập');
  const result: unknown = await response.json();
  if (!result || typeof result !== 'object' || !('access_token' in result) || typeof result.access_token !== 'string' || !result.access_token ||
      !('refresh_token' in result) || typeof result.refresh_token !== 'string' || !result.refresh_token ||
      !('expires_in' in result) || typeof result.expires_in !== 'number' || !Number.isFinite(result.expires_in) || result.expires_in <= 0) {
    throw new Error('Phản hồi đăng nhập không hợp lệ');
  }
  return { accessToken: result.access_token, refreshToken: result.refresh_token, expiresIn: result.expires_in };
}

/** Làm mới trước khi hết hạn, chỉ giữ token trong closure và gộp các yêu cầu đồng thời. */
export function createCognitoTokenProvider(config: CognitoConfig, initial: CognitoTokens, fetcher: typeof fetch = fetch) {
  const domain = domainUrl(config);
  let tokens = initial;
  let expiresAt = Date.now() + initial.expiresIn * 1000;
  let inFlight: Promise<string | null> | null = null;
  return async () => {
    if (Date.now() < expiresAt - 60_000) return tokens.accessToken;
    if (!inFlight) {
      inFlight = (async () => {
        try {
          const body = new URLSearchParams({ grant_type: 'refresh_token', client_id: config.clientId, refresh_token: tokens.refreshToken });
          const response = await fetcher(new URL('/oauth2/token', domain), { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body, credentials: 'omit', redirect: 'error' });
          if (!response.ok) return null;
          const data: unknown = await response.json();
          if (!data || typeof data !== 'object' || !('access_token' in data) || typeof data.access_token !== 'string' || !data.access_token ||
              !('expires_in' in data) || typeof data.expires_in !== 'number' || !Number.isFinite(data.expires_in) || data.expires_in <= 0) return null;
          const refresh = 'refresh_token' in data && typeof data.refresh_token === 'string' && data.refresh_token ? data.refresh_token : tokens.refreshToken;
          tokens = { accessToken: data.access_token, refreshToken: refresh, expiresIn: data.expires_in };
          expiresAt = Date.now() + data.expires_in * 1000;
          return tokens.accessToken;
        } catch { return null; }
      })().finally(() => { inFlight = null; });
    }
    return inFlight;
  };
}
