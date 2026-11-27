// Chỉ chạy với API xác thực giả và PostgreSQL brand_demo cục bộ riêng.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE);
const { execFileSync } = require('node:child_process');
const assert = require('node:assert/strict');
const path = require('node:path');
const { randomUUID } = require('node:crypto');

(async () => {
  if (process.env.TEST_ONLY_AUTH_STUB !== '1' || !process.env.DEMO_DATABASE_URL ||
      process.env.DATABASE_URL !== process.env.DEMO_DATABASE_URL) throw new Error('Chỉ dùng môi trường demo thử riêng');
  const browser = await chromium.launch({ executablePath: process.env.TEST_BROWSER, headless: true });
  try {
    const page = await browser.newPage();
    await page.goto(process.env.TEST_UI_BASE);
    await page.getByText('Kết nối bằng access token').click();
    await page.locator('input[type=password]').fill('test-token');
    await page.locator('form button').click();
    const brandName = `Mây Tea demo ${Date.now()}`;
    await page.locator('input[maxlength="200"]').fill(brandName);
    await page.locator('textarea').fill('Mây Tea');
    const created = page.waitForResponse(r => r.request().method() === 'POST' && new URL(r.url()).pathname === '/brands');
    await page.getByRole('button', { name: 'Tạo nhãn hàng', exact: true }).click();
    const brand = await (await created).json();
    await page.getByText('Đã lưu nhãn hàng và cấu hình. Lịch hoạt động khi dịch vụ lịch được bật.').waitFor();
    execFileSync(process.env.TEST_FAKE_WORKER_PYTHON, ['-m', 'app.demo_stream', '--brand-id', brand.id,
      '--batches', '2', '--interval', '1', '--comments', '3'],
      { cwd: path.resolve(__dirname, '../../backend'), env: process.env, timeout: 30000 });
    await page.getByRole('button', { name: brandName, exact: true }).click();
    await page.getByRole('button', { name: 'Tải lại nội dung' }).click();
    await page.getByText('Bài giả lập').first().waitFor();
    assert.equal(await page.getByText('Bài giả lập').count(), 2);
    assert.ok(await page.getByText(/Nguồn: Dữ liệu giả lập/).count() >= 2);
    assert.equal(await page.locator('a[href*="example.invalid"]').count(), 0);
    await page.getByLabel('Nền tảng', { exact: true }).selectOption('demo');
    await page.getByRole('button', { name: 'Lọc nội dung' }).click();
    await page.getByText('Bài giả lập').first().waitFor();
    execFileSync(process.env.TEST_FAKE_WORKER_PYTHON, ['-m', 'app.demo_history', '--brand-id', brand.id,
      '--session-id', randomUUID()], { cwd: path.resolve(__dirname, '../../backend'), env: process.env, timeout: 30000 });
    const alerts = page.locator('section').filter({ has: page.getByRole('heading', { name: 'Quy tắc cảnh báo', exact: true }) });
    const rule = alerts.locator('form').filter({ has: page.getByRole('heading', { name: 'Bình luận tiêu cực' }) });
    await rule.getByLabel('Bật quy tắc').check();
    await rule.getByLabel('Ngưỡng tăng (%)').fill('50');
    await rule.getByLabel('Độ dài mỗi cửa sổ (ngày)').fill('1');
    await rule.getByLabel('Số nội dung tối thiểu').fill('1');
    await rule.getByRole('button', { name: 'Lưu quy tắc' }).click();
    await alerts.getByText('Đã lưu quy tắc.').waitFor();
    await rule.getByRole('button', { name: 'Đánh giá cửa sổ đã hoàn tất' }).click();
    await alerts.getByText(/Kỳ trước: 10; kỳ này: 15/).waitFor();
    assert.equal(await alerts.locator('li').filter({ hasText: 'Kỳ trước: 10, kỳ này: 15' }).count(), 1);
    await rule.getByRole('button', { name: 'Đánh giá cửa sổ đã hoàn tất' }).click();
    await alerts.getByText(/Kỳ trước: 10; kỳ này: 15/).waitFor();
    assert.equal(await alerts.locator('li').filter({ hasText: 'Kỳ trước: 10, kỳ này: 15' }).count(), 1);
    console.log('Demo browser check passed: batches, source labels and 10-to-15 alert');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
