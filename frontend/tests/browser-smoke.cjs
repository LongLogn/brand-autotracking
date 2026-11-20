// Chạy với PLAYWRIGHT_MODULE trỏ đến Playwright cài ngoài dự án và TEST_UI_BASE đến Vite thử nghiệm.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE);
const assert = require('node:assert/strict');
const { execFileSync } = require('node:child_process');
const path = require('node:path');

(async () => {
  const browser = await chromium.launch({ executablePath: process.env.TEST_BROWSER, headless: true });
  try {
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', (error) => errors.push(error.message));
    await page.goto(process.env.TEST_UI_BASE);
    await page.getByText('Kết nối bằng access token').click();
    await page.locator('input[type=password]').fill('test-token');
    await page.locator('form button').click();
    await page.locator('input[maxlength="200"]').waitFor();
    await page.route('**/brands?**', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 500));
      await route.fulfill({ status: 503, contentType: 'application/json', body: '{}' });
    });
    await page.getByRole('button', { name: 'Tải lại', exact: true }).click();
    await page.getByText('Đang tải dữ liệu…').waitFor();
    assert.equal(await page.getByRole('button', { name: 'Tải lại', exact: true }).isDisabled(), true);
    await page.getByText('Yêu cầu thất bại (HTTP 503).').waitFor();
    await page.unroute('**/brands?**');
    await page.getByRole('button', { name: 'Tải lại', exact: true }).click();
    await page.getByText('Đang tải dữ liệu…').waitFor({ state: 'hidden' });
    const brandName = `Browser Test ${Date.now()}`;
    await page.locator('input[maxlength="200"]').fill(brandName);
    await page.locator('textarea').fill('coffee');
    await page.locator('form button[type=submit], form button:not([type])').last().click();
    await page.getByRole('status').waitFor();
    let configFailed = false;
    await page.route('**/brands/*/tracking', async (route) => {
      if (!configFailed && route.request().method() === 'GET') {
        configFailed = true;
        await route.abort();
      } else await route.continue();
    });
    await page.getByRole('button', { name: brandName, exact: true }).click();
    await page.getByRole('button', { name: 'Thử tải lại cấu hình' }).waitFor();
    assert.equal(await page.locator('textarea').isDisabled(), true);
    await page.getByRole('button', { name: 'Thử tải lại cấu hình' }).click();
    await page.waitForFunction(() => !document.querySelector('textarea')?.disabled);
    await page.unroute('**/brands/*/tracking');
    await page.locator('textarea').fill('coffee\nnew keyword');
    await page.getByRole('button', { name: 'Lưu thay đổi' }).click();
    await page.getByText('Đã lưu. Lịch hoạt động khi dịch vụ lịch được bật.').waitFor();
    await page.getByRole('button', { name: brandName, exact: true }).click();
    await page.waitForFunction(() => document.querySelector('textarea')?.value.includes('new keyword'));
    assert.match(await page.locator('textarea').inputValue(), /new keyword/);
    await page.getByRole('button', { name: /Tạo phiên chờ/ }).click();
    await page.getByRole('button', { name: /queued/ }).click();
    await page.getByText(/Bắt đầu: Chưa bắt đầu/).waitFor();
    assert.match(await page.locator('main').innerText(), /Chưa bắt đầu/);
    if (process.env.TEST_FAKE_WORKER_PYTHON) {
      execFileSync(process.env.TEST_FAKE_WORKER_PYTHON, ['-m', 'tests.browser_fake_worker'], {
        cwd: path.resolve(__dirname, '../../backend'), stdio: 'pipe', env: process.env,
      });
      await page.getByRole('button', { name: 'Tải lại phiên' }).click();
      await page.getByRole('button', { name: /success · Xếp hàng/ }).click();
      await page.getByText('sample', { exact: true }).waitFor();
      await page.getByRole('button', { name: 'Xem bình luận' }).click();
      await page.getByText(/sample comment/).waitFor();
      assert.match(await page.locator('main').innerText(), /Thích: 5/);
      assert.match(await page.locator('main').innerText(), /sample comment · Thích: 2/);
      await page.getByRole('button', { name: 'Tải lại nội dung' }).click();
      await page.getByRole('button', { name: 'Bình luận tổng hợp' }).click();
      await page.waitForFunction(() => [...document.querySelectorAll('li')].filter((item) => item.textContent.includes('sample comment · Thích: 2')).length === 2);
      assert.equal(await page.getByText(/sample comment · Thích: 2/).count(), 2);
      await page.getByRole('button', { name: 'Tải lại tổng quan' }).click();
      await page.getByText('Đã lưu 1 bài viết, 1 bình luận và 1 phiên tracking.').waitFor();
      assert.equal(await page.getByRole('heading', { name: 'Tổng quan', exact: true }).count(), 1);
      assert.equal(await page.getByRole('heading', { name: 'Nội dung đã thu thập', exact: true }).count(), 1);
      await page.getByLabel('Nền tảng', { exact: true }).selectOption('tiktok');
      await page.getByRole('button', { name: 'Lọc nội dung' }).click();
      await page.getByRole('button', { name: 'Bình luận tổng hợp' }).waitFor();
      await page.getByLabel('Đăng từ').fill('2026-01-01T00:00');
      await page.getByRole('button', { name: 'Lọc nội dung' }).click();
      await page.getByText('Chưa có bài viết trên trang này.').waitFor();
    }
    await page.getByRole('button', { name: /Ngắt kết nối/ }).click();
    assert.equal(await page.locator('input[type=password]').inputValue(), '');
    await page.getByText('Kết nối bằng access token').click();
    await page.locator('input[type=password]').fill('test-token');
    await page.locator('form button').click();
    const retryName = `Retry Test ${Date.now()}`;
    await page.locator('input[maxlength="200"]').fill(retryName);
    await page.locator('textarea').fill('coffee');
    let failed = false;
    let creates = 0;
    await page.route('**/brands**', async (route) => {
      const request = route.request();
      if (request.method() === 'POST' && new URL(request.url()).pathname === '/brands') creates++;
      if (!failed && request.method() === 'PUT' && request.url().endsWith('/tracking')) {
        failed = true;
        await route.abort();
      } else await route.continue();
    });
    await page.getByRole('button', { name: 'Tạo nhãn hàng', exact: true }).click();
    await page.getByRole('button', { name: 'Thử lại lưu cấu hình' }).click();
    await page.getByText('Đã lưu nhãn hàng và cấu hình. Lịch hoạt động khi dịch vụ lịch được bật.').waitFor();
    assert.equal(creates, 1);
    await page.unroute('**/brands**');
    const ambiguousName = `Ambiguous Test ${Date.now()}`;
    await page.locator('input[maxlength="200"]').fill(ambiguousName);
    await page.locator('textarea').fill('coffee');
    await page.route('**/brands', async (route) => {
      if (route.request().method() === 'POST') {
        await route.fetch();
        await route.abort();
      } else await route.continue();
    });
    await page.getByRole('button', { name: 'Tạo nhãn hàng', exact: true }).click();
    await page.getByText(/Chưa xác định được nhãn hàng đã tạo hay chưa/).waitFor();
    assert.equal(await page.getByRole('button', { name: 'Tạo nhãn hàng', exact: true }).isDisabled(), true);
    await page.unroute('**/brands');
    await page.getByRole('button', { name: 'Tải lại', exact: true }).click();
    await page.getByRole('button', { name: ambiguousName, exact: true }).waitFor();
    await page.getByRole('button', { name: 'Tôi đã kiểm tra danh sách' }).click();
    assert.equal(await page.getByRole('button', { name: 'Tạo nhãn hàng', exact: true }).isDisabled(), false);
    await page.getByRole('button', { name: 'Tạo nhãn hàng', exact: true }).click();
    await page.getByText('Đã lưu nhãn hàng và cấu hình. Lịch hoạt động khi dịch vụ lịch được bật.').waitFor();
    assert.equal(await page.getByRole('button', { name: ambiguousName, exact: true }).count(), 1);
    assert.deepEqual(errors, []);
    console.log('Browser smoke test passed');
  } finally { await browser.close(); }
})().catch((error) => { console.error(error); process.exitCode = 1; });
