/** Client thử nghiệm cho hợp đồng backend; không lưu token và chưa nối vào store mẫu. */
export type AccessTokenProvider = () => Promise<string | null>;
export interface Pagination { limit?: number; offset?: number }
export interface PostFilters { source?: string; postedFrom?: string; postedUntil?: string }
export type CommentFilters = Pick<PostFilters, 'postedFrom' | 'postedUntil'>;

export class ApiError extends Error {
  readonly status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

export interface ApiBrand { id: string; name: string }
export interface ApiTrackingConfig {
  keywords: string[];
  platforms: Array<'reddit' | 'threads' | 'facebook' | 'tiktok'>;
  frequency: 'daily' | 'twice-daily' | 'weekly';
  runTime: string;
  timezone: string;
  postLimit: number;
  active: boolean;
}
export interface ApiTrackingRead extends ApiTrackingConfig { nextRunAt?: string | null }
export interface ApiRun {
  id: string;
  queued_at: string;
  started_at: string | null;
  finished_at: string | null;
  status: 'queued' | 'running' | 'success' | 'partial' | 'failed' | 'skipped';
  error_code: string | null;
}
export interface ApiBrandOverview {
  post_count: number;
  comment_count: number;
  run_count: number;
  latest_run: ApiRun | null;
}
export interface ApiAttempt {
  id: string;
  source: string;
  keyword: string;
  status: 'success' | 'empty' | 'failed';
  result_count: number | null;
  error_code: string | null;
}
export interface ApiMetrics {
  captured_at: string;
  likes: number | null;
  comment_count: number | null;
  views: number | null;
  shares: number | null;
}
export interface ApiPost {
  id: string;
  source: string;
  source_id: string | null;
  url: string;
  title: string | null;
  content: string | null;
  posted_at: string | null;
  first_seen_at: string;
  maybe_duplicate: boolean;
  metrics: ApiMetrics | null;
}
export interface ApiComment {
  id: string;
  source_id: string | null;
  content: string;
  posted_at: string | null;
  maybe_duplicate: boolean;
  metrics: ApiMetrics | null;
}

/** Base URL đến từ cấu hình ứng dụng tin cậy, token do hệ thống đăng nhập cung cấp. */
export function createApiClient(baseUrl: string, tokenProvider: AccessTokenProvider, fetcher: typeof fetch = fetch) {
  const base = new URL(baseUrl);
  const local = ['localhost', '127.0.0.1', '[::1]'].includes(base.hostname);
  if ((base.protocol !== 'https:' && !(local && base.protocol === 'http:')) || base.username || base.password || base.search || base.hash) {
    throw new Error('Địa chỉ API không hợp lệ');
  }
  base.pathname = `${base.pathname.replace(/\/+$/, '')}/`;

  async function request<T>(path: string, method: 'GET' | 'POST' | 'PUT' = 'GET', body?: unknown, signal?: AbortSignal, idempotencyKey?: string): Promise<T> {
    const token = await tokenProvider();
    if (!token) throw new ApiError(401, 'Cần đăng nhập');
    const headers: Record<string, string> = { Authorization: `Bearer ${token}` };
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    if (idempotencyKey) headers['Idempotency-Key'] = idempotencyKey;
    const response = await fetcher(new URL(path, base), {
      method, headers, body: body === undefined ? undefined : JSON.stringify(body),
      credentials: 'omit', redirect: 'error', signal,
    });
    if (!response.ok) throw new ApiError(response.status, 'Không thể hoàn thành yêu cầu');
    return response.json() as Promise<T>;
  }
  const brandPath = (id: string) => `brands/${encodeURIComponent(id)}`;
  const runPath = (brandId: string, runId: string) => `${brandPath(brandId)}/runs/${encodeURIComponent(runId)}`;
  const page = (path: string, pagination?: Pagination, filters?: PostFilters) => {
    if (!pagination && !filters) return path;
    const query = new URLSearchParams();
    if (pagination?.limit !== undefined) query.set('limit', String(pagination.limit));
    if (pagination?.offset !== undefined) query.set('offset', String(pagination.offset));
    if (filters?.source) query.set('source', filters.source);
    if (filters?.postedFrom) query.set('posted_from', filters.postedFrom);
    if (filters?.postedUntil) query.set('posted_until', filters.postedUntil);
    const suffix = query.toString();
    return suffix ? `${path}?${suffix}` : path;
  };
  return {
    listBrands: (signal?: AbortSignal, pagination?: Pagination) => request<ApiBrand[]>(page('brands', pagination), 'GET', undefined, signal),
    createBrand: (name: string, signal?: AbortSignal, idempotencyKey?: string) => request<ApiBrand>('brands', 'POST', { name }, signal, idempotencyKey),
    renameBrand: (id: string, name: string, signal?: AbortSignal) => request<ApiBrand>(brandPath(id), 'PUT', { name }, signal),
    getTracking: (id: string, signal?: AbortSignal) => request<ApiTrackingRead>(`${brandPath(id)}/tracking`, 'GET', undefined, signal),
    setTracking: (id: string, config: ApiTrackingConfig, signal?: AbortSignal) => request<ApiTrackingConfig>(`${brandPath(id)}/tracking`, 'PUT', config, signal),
    getOverview: (id: string, signal?: AbortSignal) => request<ApiBrandOverview>(`${brandPath(id)}/overview`, 'GET', undefined, signal),
    listRuns: (id: string, signal?: AbortSignal, pagination?: Pagination) => request<ApiRun[]>(page(`${brandPath(id)}/runs`, pagination), 'GET', undefined, signal),
    queueRun: (id: string, signal?: AbortSignal) => request<{ id: string; status: 'queued' }>(`${brandPath(id)}/runs`, 'POST', undefined, signal),
    getRun: (brandId: string, runId: string, signal?: AbortSignal) => request<ApiRun & { attempts: ApiAttempt[]; collection_limits: { search_pages: number; comment_pages: number } | null }>(runPath(brandId, runId), 'GET', undefined, signal),
    listRunPosts: (brandId: string, runId: string, signal?: AbortSignal, pagination?: Pagination) => request<ApiPost[]>(page(`${runPath(brandId, runId)}/mentions`, pagination), 'GET', undefined, signal),
    listAttemptPosts: (brandId: string, runId: string, attemptId: string, signal?: AbortSignal, pagination?: Pagination) => request<ApiPost[]>(page(`${runPath(brandId, runId)}/attempts/${encodeURIComponent(attemptId)}/mentions`, pagination), 'GET', undefined, signal),
    listRunComments: (brandId: string, runId: string, postId: string, signal?: AbortSignal, pagination?: Pagination, filters?: CommentFilters) => request<ApiComment[]>(page(`${runPath(brandId, runId)}/mentions/${encodeURIComponent(postId)}/comments`, pagination, filters), 'GET', undefined, signal),
    listPosts: (brandId: string, signal?: AbortSignal, pagination?: Pagination, filters?: PostFilters) => request<ApiPost[]>(page(`${brandPath(brandId)}/mentions`, pagination, filters), 'GET', undefined, signal),
    listComments: (brandId: string, postId: string, signal?: AbortSignal, pagination?: Pagination, filters?: CommentFilters) => request<ApiComment[]>(page(`${brandPath(brandId)}/mentions/${encodeURIComponent(postId)}/comments`, pagination, filters), 'GET', undefined, signal),
  };
}
