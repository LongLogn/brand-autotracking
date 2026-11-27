// Kịch bản demo theo phút: mốc 20/100 → tiêu cực 60/200 (cảnh báo) → tích cực 65/300.
// Chỉ chạy với API xác thực giả và PostgreSQL brand_demo cục bộ riêng.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE);
const { execFileSync } = require('node:child_process');
const assert = require('node:assert/strict');
const path = require('node:path');

function scenario(brandId, batches, sessionId) {
  const args = ['-m', 'app.demo_stream', '--scenario', '--brand-id', brandId, '--batches', String(batches), '--interval', '1'];
  if (sessionId) args.push('--session-id', sessionId);
  const output = execFileSync(process.env.TEST_FAKE_WORKER_PYTHON, args,
    { cwd: path.resolve(__dirname, '../../backend'), env: process.env, timeout: 60000 }).toString();
  return output.match(/demo_session=([0-9a-f-]{36})/)[1];
}

async function connect(page) {
  await page.getByText('Kết nối bằng access token').click();
  await page.locator('input[type=password]').fill('test-token');
  await page.locator('form button').click();
}

// Giao diện chia tab: mở tab trước khi thao tác với nội dung bên trong.
const openTab = (page, name) => page.getByRole('tab', { name, exact: true }).click();
(async () => {
  if (process.env.TEST_ONLY_AUTH_STUB !== '1' || !process.env.DEMO_DATABASE_URL ||
      process.env.DATABASE_URL !== process.env.DEMO_DATABASE_URL) throw new Error('Chỉ dùng môi trường demo thử riêng');
  const browser = await chromium.launch({ executablePath: process.env.TEST_BROWSER, headless: true });
  try {
    const page = await browser.newPage();
    await page.goto(process.env.TEST_UI_BASE);
    await connect(page);
    const brandName = `KFCC demo ${Date.now()}`;
    await page.locator('input[maxlength="200"]').fill(brandName);
    await page.locator('textarea').fill('KFCC');
    const created = page.waitForResponse(r => r.request().method() === 'POST' && new URL(r.url()).pathname === '/brands');
    await page.getByRole('button', { name: 'Tạo nhãn hàng', exact: true }).click();
    const brand = await (await created).json();
    await page.getByText('Đã lưu nhãn hàng và cấu hình. Lịch hoạt động khi dịch vụ lịch được bật.').waitFor();
    await page.getByRole('button', { name: brandName, exact: true }).click();
    await openTab(page, 'Cảnh báo');

    const rules = page.locator('section').filter({ has: page.getByRole('heading', { name: 'Quy tắc cảnh báo', exact: true }) });
    const rule = rules.locator('form').filter({ has: page.getByRole('heading', { name: 'Bình luận tiêu cực' }) });
    await rule.getByLabel('Bật quy tắc').check();
    await rule.getByLabel('Ngưỡng tăng (%)').fill('50');
    await rule.getByLabel('Độ dài mỗi cửa sổ (ngày)').fill('1');
    await rule.getByLabel('Số nội dung tối thiểu').fill('10');
    await rule.getByRole('button', { name: 'Lưu quy tắc' }).click();
    await rules.getByText('Đã lưu quy tắc.').waitFor();

    const live = page.locator('#live-alerts');
    const sessionId = scenario(brand.id, 1);
    await live.locator('tbody tr').first().waitFor({ timeout: 20000 });
    assert.match(await live.locator('tbody tr').nth(0).innerText(), /20 \/ 100\s+20%\s+Mốc/);
    assert.equal(await live.getByRole('alert').count(), 0);

    scenario(brand.id, 1, sessionId);
    await live.locator('tbody tr').nth(1).waitFor({ timeout: 20000 });
    assert.match(await live.locator('tbody tr').nth(1).innerText(), /60 \/ 200\s+30%\s+Cảnh báo/);
    await live.getByText('Bình luận tiêu cực tăng vượt ngưỡng').waitFor({ timeout: 20000 });
    assert.match(await live.getByRole('alert').innerText(), /20% \(20\/100\) lên 30% \(60\/200\)/);

    await live.getByRole('button', { name: 'Đánh giá lại lần thu thập gần nhất' }).click();
    await live.getByText(/không tạo cảnh báo trùng/).waitFor();
    await rules.getByRole('button', { name: 'Tải lại quy tắc' }).click();
    await rules.locator('li').filter({ hasText: 'Tỷ lệ tiêu cực 20% → 30%' }).first().waitFor();
    assert.equal(await rules.locator('li').filter({ hasText: 'Tỷ lệ tiêu cực 20% → 30%' }).count(), 1);

    scenario(brand.id, 1, sessionId);
    await live.locator('tbody tr').nth(2).waitFor({ timeout: 20000 });
    assert.match(await live.locator('tbody tr').nth(2).innerText(), /65 \/ 300\s+22%\s+Không cảnh báo/);
    assert.equal(await live.locator('tbody tr').filter({ hasText: 'Cảnh báo' }).filter({ hasNotText: 'Không' }).count(), 1);

    // Liên kết trong email mở thẳng nhãn hàng và phần cảnh báo sau khi đăng nhập.
    const alerts = await (await page.request.get(new URL(`/brands/${brand.id}/alerts`, process.env.TEST_API_BASE).href,
      { headers: { Authorization: 'Bearer test-token' } })).json();
    assert.equal(alerts.length, 1);
    const linked = await browser.newPage();
    await linked.goto(`${process.env.TEST_UI_BASE}/?brand=${brand.id}&alert=${alerts[0].id}`);
    await linked.waitForURL((url) => url.search === '');
    await connect(linked);
    await linked.getByRole('heading', { name: brandName, exact: true }).waitFor();
    assert.equal(await linked.getByRole('tab', { name: 'Cảnh báo', exact: true }).getAttribute('aria-selected'), 'true');
    await linked.getByText(/Bạn mở từ email cảnh báo/).waitFor({ timeout: 20000 });
    console.log('Demo minute browser check passed: baseline, ratio alert, no duplicate, recovery and email link');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
