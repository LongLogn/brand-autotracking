import assert from 'node:assert/strict';
import test from 'node:test';
import { ApiError, createApiClient } from '../src/lib/api.ts';

test('xóa nhãn hàng gửi DELETE và giữ trạng thái xung đột', async () => {
  const calls: Array<{ url: string; options?: RequestInit }> = [];
  const fetcher: typeof fetch = async (url, options) => {
    calls.push({ url: String(url), options });
    return calls.length === 1 ? Response.json({ deleted: true }) : Response.json({}, { status: 409 });
  };
  const api = createApiClient('https://api.example.test', async () => 'token-test', fetcher);
  assert.deepEqual(await api.deleteBrand('brand/id'), { deleted: true });
  assert.equal(calls[0].url, 'https://api.example.test/brands/brand%2Fid');
  assert.equal(calls[0].options?.method, 'DELETE');
  await assert.rejects(api.deleteBrand('brand/id'), (error: unknown) => error instanceof ApiError && error.status === 409);
});

test('gửi bearer tới base URL tin cậy, không theo redirect', async () => {
  let seenUrl = '';
  let seen: RequestInit | undefined;
  const fakeFetch: typeof fetch = async (url, options) => {
    seenUrl = String(url);
    seen = options;
    return Response.json({ id: '1', name: 'Tên' }, { status: 201 });
  };
  const api = createApiClient('https://api.example.test/stage', async () => 'token-test', fakeFetch);
  assert.deepEqual(await api.createBrand('Tên', undefined, 'request-id'), { id: '1', name: 'Tên' });
  assert.equal(seenUrl, 'https://api.example.test/stage/brands');
  assert.equal((seen?.headers as Record<string, string>).Authorization, 'Bearer token-test');
  assert.equal((seen?.headers as Record<string, string>)['Idempotency-Key'], 'request-id');
  assert.equal(seen?.redirect, 'error');
  assert.equal(seen?.credentials, 'omit');
  assert.equal(seen?.body, JSON.stringify({ name: 'Tên' }));
});

test('không gửi request khi thiếu token; không hiển thị body lỗi', async () => {
  let called = false;
  const fakeFetch: typeof fetch = async () => { called = true; return Response.json({ message: 'private' }, { status: 403 }); };
  await assert.rejects(createApiClient('http://127.0.0.1:8000', async () => null, fakeFetch).listBrands(),
    (error: unknown) => error instanceof ApiError && error.status === 401);
  assert.equal(called, false);
  await assert.rejects(createApiClient('https://api.example.test', async () => 'token-test', fakeFetch).listBrands(),
    (error: unknown) => error instanceof ApiError && error.status === 403 && !error.message.includes('private'));
});

test('từ chối base URL không an toàn và mã hóa ID trong đường dẫn', async () => {
  assert.throws(() => createApiClient('http://example.test', async () => null));
  assert.throws(() => createApiClient('https://u:p@example.test', async () => null));
  let seenUrl = '';
  const fakeFetch: typeof fetch = async (url) => { seenUrl = String(url); return Response.json([]); };
  await createApiClient('https://api.example.test', async () => 't', fakeFetch).listRuns('a/b');
  assert.equal(seenUrl, 'https://api.example.test/brands/a%2Fb/runs');
});

test('đổi tên và truyền phân trang cho danh sách', async () => {
  const calls: Array<{ url: string; options?: RequestInit }> = [];
  const fakeFetch: typeof fetch = async (url, options) => {
    calls.push({ url: String(url), options });
    return Response.json(options?.method === 'PUT' ? { id: 'a', name: 'Mới' } : []);
  };
  const api = createApiClient('https://api.example.test', async () => 't', fakeFetch);
  await api.renameBrand('a', 'Mới');
  assert.equal(calls[0].options?.method, 'PUT');
  assert.equal(calls[0].options?.body, JSON.stringify({ name: 'Mới' }));
  await api.listRunComments('a', 'b', 'c', undefined, { limit: 20, offset: 40 }, { postedUntil: '2026-02-01T00:00:00Z' });
  assert.equal(calls[1].url, 'https://api.example.test/brands/a/runs/b/mentions/c/comments?limit=20&offset=40&posted_until=2026-02-01T00%3A00%3A00Z');
  await api.getOverview('a');
  assert.equal(calls[2].url, 'https://api.example.test/brands/a/overview');
  await api.listPosts('a', undefined, { limit: 10, offset: 0 }, { source: 'tiktok', postedFrom: '2026-01-01T00:00:00Z' });
  assert.equal(calls[3].url, 'https://api.example.test/brands/a/mentions?limit=10&offset=0&source=tiktok&posted_from=2026-01-01T00%3A00%3A00Z');
  await api.listComments('a', 'c', undefined, { limit: 10 }, { postedFrom: '2026-01-01T00:00:00Z' });
  assert.equal(calls[4].url, 'https://api.example.test/brands/a/mentions/c/comments?limit=10&posted_from=2026-01-01T00%3A00%3A00Z');
});

test('trích xuất detail an toàn trong danh sách cho phép với lỗi 409 và 422, chặn nội dung lạ', async () => {
  const pausedFetch: typeof fetch = async () => Response.json({ detail: 'Cấu hình tracking đang tạm dừng' }, { status: 409 });
  await assert.rejects(createApiClient('https://api.example.test', async () => 't', pausedFetch).queueRun('b1'),
    (error: unknown) => error instanceof ApiError && error.status === 409 && error.detail === 'Cấu hình tracking đang tạm dừng');

  const dupKeywordFetch: typeof fetch = async () => Response.json(
    { detail: [{ msg: 'Value error, Từ khóa phải khác nhau và không rỗng' }] }, { status: 422 });
  await assert.rejects(createApiClient('https://api.example.test', async () => 't', dupKeywordFetch).setTracking('b1', {
    keywords: ['A', 'a'], platforms: ['tiktok'], frequency: 'daily', runTime: '08:00', timezone: 'Asia/Ho_Chi_Minh', postLimit: 1, active: true,
  }), (error: unknown) => error instanceof ApiError && error.status === 422 && error.detail === 'Từ khóa phải khác nhau và không rỗng');

  const unknownFetch: typeof fetch = async () => Response.json({ detail: 'internal stacktrace secret' }, { status: 409 });
  await assert.rejects(createApiClient('https://api.example.test', async () => 't', unknownFetch).queueRun('b1'),
    (error: unknown) => error instanceof ApiError && error.status === 409 && error.detail === undefined && !error.message.includes('secret'));
});
