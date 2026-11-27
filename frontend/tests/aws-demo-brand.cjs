// Tài khoản do harness quản lý; không ghi token, email hoặc mật khẩu ra log.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE);
const fs = require('node:fs');
(async () => {
  const browser = await chromium.launch({ executablePath: process.env.TEST_BROWSER, headless: true });
  try {
    const page = await browser.newPage();
    await page.goto(process.env.TEST_UI_BASE);
    await page.getByRole('button', { name: 'Đăng nhập với Cognito' }).click();
    await page.locator('input[name="username"]:visible').first().fill(process.env.TEST_COGNITO_USERNAME);
    await page.locator('input[name="password"]:visible').first().fill(process.env.TEST_COGNITO_PASSWORD);
    await page.locator('button[type="submit"]:visible, input[type="submit"]:visible').first().click();
    await page.getByRole('heading', { name: 'Quản lý nhãn hàng' }).waitFor({ timeout: 30000 });
    await page.locator('input[maxlength="200"]').fill('Mây Tea giả lập');
    await page.locator('textarea').fill('Mây Tea');
    const response = page.waitForResponse(r => r.request().method() === 'POST' && r.url() === `${process.env.TEST_AWS_API_BASE}/brands`);
    await page.getByRole('button', { name: 'Tạo nhãn hàng', exact: true }).click();
    const result = await response;
    if (result.status() !== 201) throw new Error(`Tạo nhãn hàng lỗi ${result.status()}`);
    const brand = await result.json();
    await page.getByText('Đã lưu nhãn hàng và cấu hình. Lịch hoạt động khi dịch vụ lịch được bật.').waitFor();
    console.log(`DEMO_BRAND_ID=${brand.id}`);
    if (process.env.TEST_DEMO_SIGNAL) {
      const deadline = Date.now() + 15 * 60 * 1000;
      while (!fs.existsSync(process.env.TEST_DEMO_SIGNAL) && Date.now() < deadline)
        await new Promise(resolve => setTimeout(resolve, 1000));
      if (!fs.existsSync(process.env.TEST_DEMO_SIGNAL)) throw new Error('Quá thời gian chuẩn bị môi trường demo');
      await page.getByRole('button', { name: 'Mây Tea giả lập', exact: true }).click();
      await page.getByRole('button', { name: 'Tải lại nội dung' }).click();
      await page.getByText('Bài giả lập').first().waitFor({ timeout: 30000 });
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
      if (process.env.TEST_DEMO_ANALYSIS === '1') {
        const analysis = page.locator('section').filter({ has: page.getByRole('heading', { name: 'Phân tích AI', exact: true }) });
        const localTime = (date) => new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
        await analysis.getByLabel('Thu thập từ').fill(localTime(new Date(Date.now() - 3 * 86400000)));
        await analysis.getByLabel('Thu thập trước').fill(localTime(new Date(Date.now() - 60000)));
        const analysisResponse = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith('/analyses'));
        await analysis.getByRole('button', { name: 'Tạo phân tích' }).click();
        const response = await analysisResponse;
        const result = await response.json();
        if (response.status() !== 200 || result.status !== 'success' || !result.findings?.length)
          throw new Error(`Phân tích không thành công: HTTP ${response.status()}, ${result.status || 'unknown'}, ${result.error_code || 'none'}`);
        console.log('AWS_DEMO_BEDROCK_OK');
      }
      console.log('AWS_DEMO_UI_OK');
    }
  } finally { await browser.close(); }
})().catch(error => { console.error(error.message); process.exitCode = 1; });
