// Chỉ chạy với Cognito demo cô lập; email và mật khẩu chỉ tồn tại trong bộ nhớ.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE);
const { randomUUID, randomBytes } = require('node:crypto');
const fs = require('node:fs');
// Giao diện chia tab: mở tab trước khi thao tác với nội dung bên trong.
const openTab = (page, name) => page.getByRole('tab', { name, exact: true }).click();
(async () => {
  const ui = new URL(process.env.TEST_UI_BASE);
  const local = ['localhost', '127.0.0.1'].includes(ui.hostname);
  const hosted = process.env.TEST_DEMO_HOSTED === '1' && ui.protocol === 'https:' && ui.hostname.endsWith('.cloudfront.net');
  if (process.env.TEST_DEMO_SIGNUP !== '1' || (!local && !hosted))
    throw new Error('Chỉ chạy với giao diện demo cục bộ và pool thử riêng');
  const browser = await chromium.launch({ executablePath: process.env.TEST_BROWSER, headless: true });
  let context;
  try {
    const options = process.env.TEST_DEMO_VIDEO_DIR ? { recordVideo: { dir: process.env.TEST_DEMO_VIDEO_DIR, size: { width: 1280, height: 720 } }, viewport: { width: 1280, height: 720 } } : {};
    context = await browser.newContext(options);
    const page = await context.newPage();
    const hold = async () => { if (process.env.TEST_DEMO_VIDEO_DIR) await page.waitForTimeout(2500); };
    const email = `demo-${randomUUID()}@example.invalid`;
    const password = `Aa1!${randomBytes(18).toString('hex')}`;
    await page.goto(process.env.TEST_UI_BASE);
    await page.getByRole('button', { name: 'Tạo tài khoản' }).click();
    await page.waitForURL('https://*.amazoncognito.com/signup?**', { timeout: 30000 });
    if (new URL(page.url()).hostname !== process.env.TEST_DEMO_AUTH_HOST) throw new Error('Sai Cognito demo');
    await page.locator('input[name="username"]:visible, input[name="email"]:visible').first().fill(email);
    const passwords = page.locator('input[type="password"]:visible');
    await passwords.first().fill(password);
    if (await passwords.count() > 1) await passwords.nth(1).fill(password);
    await hold();
    await page.locator('button[type="submit"]:visible, input[type="submit"]:visible').first().click();
    await page.getByRole('heading', { name: 'Quản lý nhãn hàng' }).waitFor({ timeout: 60000 });
    await page.locator('input[maxlength="200"]').fill('KFCC tài khoản mới');
    await page.locator('textarea').fill('KFCC');
    await hold();
    const response = page.waitForResponse(r => r.request().method() === 'POST' && r.url() === `${process.env.TEST_AWS_API_BASE}/brands`);
    await page.getByRole('button', { name: 'Tạo nhãn hàng', exact: true }).click();
    const result = await response;
    if (result.status() !== 201) throw new Error(`Tạo thương hiệu lỗi ${result.status()}`);
    const brand = await result.json();
    await page.getByText('Đã lưu nhãn hàng và cấu hình. Lịch hoạt động khi dịch vụ lịch được bật.').waitFor();
    console.log(`DEMO_BRAND_ID=${brand.id}`);
    if (process.env.TEST_DEMO_SIGNAL) {
      const deadline = Date.now() + 15 * 60 * 1000;
      while (!fs.existsSync(process.env.TEST_DEMO_SIGNAL) && Date.now() < deadline)
        await new Promise(resolve => setTimeout(resolve, 1000));
      if (!fs.existsSync(process.env.TEST_DEMO_SIGNAL)) throw new Error('Quá thời gian chuẩn bị demo');
      await page.getByRole('button', { name: 'KFCC tài khoản mới', exact: true }).click();
      await page.getByText(`Mã nhãn hàng cho người vận hành demo: ${brand.id}`).waitFor();
      await openTab(page, 'Nội dung');
      const refreshed = page.waitForResponse(r => r.request().method() === 'GET' && r.url().includes(`/brands/${brand.id}/mentions?`));
      await page.getByRole('button', { name: 'Tải lại nội dung' }).click();
      await refreshed;
      await page.getByText('Bài giả lập').first().waitFor({ timeout: 30000 });
      await page.getByText('[DỮ LIỆU GIẢ] KFCC ra mắt combo gà rán mới.', { exact: true }).first().waitFor({ timeout: 30000 });
      const batches = page.locator('article').filter({ has: page.getByText('[DỮ LIỆU GIẢ] KFCC ra mắt combo gà rán mới.', { exact: true }) });
      await batches.nth(1).waitFor({ timeout: 30000 });
      const batchCount = await batches.count();
      if (batchCount !== 2) throw new Error(`Số đợt giả không đúng: ${batchCount}`);
      const positiveCounts = [];
      for (let i = 0; i < 2; i++) {
        const batch = batches.nth(i);
        await batch.getByRole('button', { name: 'Bình luận tổng hợp' }).click();
        await batch.locator('li').first().waitFor();
        const comments = await batch.locator('li').allTextContents();
        positiveCounts.push(comments.filter(text => text.includes('thích sản phẩm') || text.includes('thơm ngon')).length);
        await hold();
      }
      if (positiveCounts.sort().join(',') !== '2,4') throw new Error('Diễn biến hai đợt giả không đúng kịch bản');
      await openTab(page, 'Cảnh báo');
      const alerts = page.locator('section').filter({ has: page.getByRole('heading', { name: 'Quy tắc cảnh báo', exact: true }) });
      const rule = alerts.locator('form').filter({ has: page.getByRole('heading', { name: 'Bình luận tiêu cực' }) });
      await rule.getByLabel('Bật quy tắc').check();
      await rule.getByLabel('Ngưỡng tăng (%)').fill('50');
      await rule.getByLabel('Độ dài mỗi cửa sổ (ngày)').fill('1');
      await rule.getByLabel('Số nội dung tối thiểu').fill('1');
      await rule.getByRole('button', { name: 'Lưu quy tắc' }).click();
      await alerts.getByText('Đã lưu quy tắc.').waitFor();
      await rule.getByRole('button', { name: 'Đánh giá cửa sổ đã hoàn tất' }).click();
      await alerts.getByText(/Kỳ trước: 10; kỳ này: 15/).waitFor({ timeout: 30000 });
      await alerts.locator('li').filter({ hasText: 'Kỳ trước: 10, kỳ này: 15' }).waitFor();
      await alerts.locator('li').filter({ hasText: 'Kỳ trước: 10, kỳ này: 15' }).scrollIntoViewIfNeeded();
      await hold();
      if (process.env.TEST_DEMO_ANALYSIS === '1') {
        await openTab(page, 'Phân tích AI');
        const analysis = page.locator('section').filter({ has: page.getByRole('heading', { name: 'Phân tích AI', exact: true }) });
        const localTime = date => new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
        const now = new Date();
        const end = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
        await analysis.getByLabel('Thu thập từ').fill(localTime(new Date(end.getTime() - 3 * 86400000)));
        await analysis.getByLabel('Thu thập trước').fill(localTime(end));
        let passed = false;
        for (let attempt = 0; attempt < 2 && !passed; attempt++) {
          const response = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith('/analyses'));
          await analysis.getByRole('button', { name: 'Tạo phân tích' }).click();
          const r = await response; const job = await r.json();
          passed = r.status() === 200 && job.status === 'success' && !!job.findings?.length;
          if (!passed) console.log(`AI_ATTEMPT_FAILED status=${job.status || 'unknown'} code=${job.error_code || 'none'}`);
          if (!passed && attempt === 0) await analysis.getByRole('button', { name: 'Tạo phân tích' }).waitFor({ state: 'visible' });
        }
        if (!passed) throw new Error('AI không trả phân tích thành công sau tối đa hai lượt');
      }
      console.log(process.env.TEST_DEMO_ANALYSIS === '1' ? 'DEMO_COMPLETE_FLOW_OK' : 'DEMO_CORE_FLOW_OK');
    }
    console.log('DEMO_SIGNUP_AND_BRAND_OK');
  } finally { if (context) await context.close(); await browser.close(); }
})().catch(error => { console.error(error.message); process.exitCode = 1; });
