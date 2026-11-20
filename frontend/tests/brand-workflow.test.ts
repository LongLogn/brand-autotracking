import assert from 'node:assert/strict';
import test from 'node:test';
import { createBrandWithTracking, retryBrandTracking } from '../src/lib/brand-workflow.ts';
import type { ApiTrackingConfig } from '../src/lib/api.ts';

const config: ApiTrackingConfig = { keywords: ['cafe'], platforms: ['tiktok'], frequency: 'daily',
  runTime: '08:00', timezone: 'Asia/Ho_Chi_Minh', postLimit: 2, active: true };

test('trả ID đã tạo khi lưu cấu hình lỗi và chỉ thử lại cấu hình', async () => {
  let creates = 0;
  let saves = 0;
  const api = {
    createBrand: async () => { creates++; return { id: 'brand-1', name: 'Cafe' }; },
    setTracking: async (id: string) => {
      assert.equal(id, 'brand-1');
      if (++saves === 1) throw new Error('network');
      return config;
    },
  };
  const result = await createBrandWithTracking(api, 'Cafe', config);
  assert.equal(result.status, 'tracking-failed');
  if (result.status !== 'tracking-failed') return;
  assert.deepEqual(await retryBrandTracking(api, result.brand, config), config);
  assert.equal(creates, 1);
  assert.equal(saves, 2);
});

test('lỗi tạo được chuyển tiếp và không gọi lưu cấu hình', async () => {
  let saved = false;
  const api = {
    createBrand: async () => { throw new Error('create failed'); },
    setTracking: async () => { saved = true; return config; },
  };
  await assert.rejects(createBrandWithTracking(api, 'Cafe', config), /create failed/);
  assert.equal(saved, false);
});

test('trả cấu hình và nhãn hàng sau khi lưu thành công', async () => {
  const api = { createBrand: async () => ({ id: '1', name: 'Cafe' }), setTracking: async () => config };
  assert.deepEqual(await createBrandWithTracking(api, 'Cafe', config),
    { status: 'complete', brand: { id: '1', name: 'Cafe' }, tracking: config });
});
