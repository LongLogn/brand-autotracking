import assert from 'node:assert/strict';
import test from 'node:test';
import { attemptView, commentView, loadRunPage, postView, runView } from '../src/lib/tracking-view.ts';

test('phiên chờ giữ thời điểm xếp hàng và thời điểm bắt đầu rỗng', () => {
  const result = runView({ id: '1', status: 'queued', queued_at: '2026-11-16T00:00:00Z',
    started_at: null, finished_at: null, error_code: null });
  assert.equal(result.queuedAt, '2026-11-16T00:00:00Z');
  assert.equal(result.startedAt, null);
});

test('tải chi tiết và trang được yêu cầu, chuyển tiếp lỗi thay vì báo dữ liệu rỗng', async () => {
  let received: unknown;
  const api = {
    getRun: async () => ({ id: 'r', status: 'queued' as const, queued_at: '2026-11-16T00:00:00Z',
      started_at: null, finished_at: null, error_code: null, attempts: [], collection_limits: null }),
    listRunPosts: async (_brand: string, _run: string, _signal?: AbortSignal, page?: { limit?: number; offset?: number }) => {
      received = page;
      return [];
    },
    listRunComments: async () => [],
  };
  const page = await loadRunPage(api, 'b', 'r', { limit: 10, offset: 20 });
  assert.deepEqual(received, { limit: 10, offset: 20 });
  assert.equal(page.run.startedAt, null);
  await assert.rejects(loadRunPage({ ...api, listRunPosts: async () => { throw new Error('network'); } }, 'b', 'r'), /network/);
});

test('giữ null khác 0 và giữ cờ có thể trùng', () => {
  const attempt = attemptView({ id: 'a', source: 'tiktok', keyword: 'x', status: 'failed', result_count: null, error_code: 'error' });
  assert.equal(attempt.resultCount, null);
  const post = postView({ id: 'p', source: 'tiktok', source_id: null, url: 'https://example.test', title: null,
    content: null, posted_at: null, first_seen_at: '2026-11-16T00:00:00Z', maybe_duplicate: true,
    metrics: { captured_at: '2026-11-16T00:00:00Z', likes: 0, comment_count: null, views: null, shares: null } });
  assert.equal(post.likes, 0);
  assert.equal(post.commentCount, null);
  assert.equal(post.maybeDuplicate, true);
  assert.equal(commentView({ id: 'c', source_id: null, content: 'x', posted_at: null, maybe_duplicate: true, metrics: null }).likes, null);
});
