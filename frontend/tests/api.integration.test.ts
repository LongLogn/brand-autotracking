import assert from 'node:assert/strict';
import test from 'node:test';
import { createApiClient } from '../src/lib/api.ts';
import { createBrandWithTracking } from '../src/lib/brand-workflow.ts';
import { loadRunPage } from '../src/lib/tracking-view.ts';

const testBase = process.env.TEST_API_BASE;

test('client giao tiếp backend thật với xác thực và database giả lập', { skip: !testBase }, async () => {
  const preflight = await fetch(`${testBase}/brands`, { method: 'OPTIONS', headers: {
    Origin: 'http://localhost:5173', 'Access-Control-Request-Method': 'POST',
    'Access-Control-Request-Headers': 'authorization,content-type',
  } });
  assert.equal(preflight.status, 200);
  assert.equal(preflight.headers.get('access-control-allow-origin'), 'http://localhost:5173');
  const blocked = await fetch(`${testBase}/brands`, { method: 'OPTIONS', headers: {
    Origin: 'https://untrusted.example', 'Access-Control-Request-Method': 'POST',
  } });
  assert.equal(blocked.status, 400);
  const api = createApiClient(testBase!, async () => 'test-token');
  const config = { keywords: ['sample'], platforms: ['tiktok'] as const, frequency: 'daily' as const,
    runTime: '08:00', timezone: 'Asia/Ho_Chi_Minh', postLimit: 2, active: true };
  const created = await createBrandWithTracking(api, `Test ${crypto.randomUUID()}`, { ...config, platforms: [...config.platforms] });
  assert.equal(created.status, 'complete');
  const brand = created.brand;
  assert.ok(brand.id);
  assert.equal((await api.getTracking(brand.id)).postLimit, 2);
  const queued = await api.queueRun(brand.id);
  assert.equal(queued.status, 'queued');
  const run = await api.getRun(brand.id, queued.id);
  assert.equal(run.status, 'queued');
  assert.equal(run.started_at, null);
  assert.ok(run.queued_at);
  assert.deepEqual(run.collection_limits, { search_pages: 1, comment_pages: 1 });
  assert.deepEqual(await api.listRunPosts(brand.id, queued.id), []);
  const page = await loadRunPage(api, brand.id, queued.id, { limit: 10, offset: 0 });
  assert.equal(page.run.startedAt, null);
  assert.deepEqual(page.posts, []);
});
