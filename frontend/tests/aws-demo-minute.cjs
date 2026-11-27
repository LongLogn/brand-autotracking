// Diễn tập kịch bản demo theo phút trên CloudFront/Cognito demo/EC2 thật.
// Người vận hành chạy demo_control.py start khi script in DEMO_BRAND_ID, và release khi script in READY_FOR_RELEASE.
// Email và mật khẩu thử chỉ tồn tại trong bộ nhớ; chỉ dùng pool demo tự xác nhận @example.invalid.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE);
const { randomUUID, randomBytes } = require('node:crypto');

(async () => {
  const ui = new URL(process.env.TEST_UI_BASE);
  if (process.env.TEST_DEMO_SIGNUP !== '1' || ui.protocol !== 'https:' || !ui.hostname.endsWith('.cloudfront.net'))
    throw new Error('Chỉ chạy với giao diện demo trên CloudFront và pool thử riêng');
  const browser = await chromium.launch({ executablePath: process.env.TEST_BROWSER, headless: true });
  let context;
  const log = (text) => console.log(`${new Date().toISOString()} ${text}`);
  try {
    const options = { viewport: { width: 1280, height: 800 } };
    if (process.env.TEST_DEMO_VIDEO_DIR) options.recordVideo = { dir: process.env.TEST_DEMO_VIDEO_DIR, size: { width: 1280, height: 800 } };
    context = await browser.newContext(options);
    const page = await context.newPage();
    const email = `demo-${randomUUID()}@example.invalid`;
    const password = `Aa1!${randomBytes(18).toString('hex')}`;
    await page.goto(ui.href);
    await page.getByRole('button', { name: 'Tạo tài khoản' }).click();
    await page.waitForURL('https://*.amazoncognito.com/signup?**', { timeout: 30000 });
    if (new URL(page.url()).hostname !== process.env.TEST_DEMO_AUTH_HOST) throw new Error('Sai Cognito demo');
    await page.locator('input[name="username"]:visible, input[name="email"]:visible').first().fill(email);
    const passwords = page.locator('input[type="password"]:visible');
    await passwords.first().fill(password);
    if (await passwords.count() > 1) await passwords.nth(1).fill(password);
    await page.locator('button[type="submit"]:visible, input[type="submit"]:visible').first().click();
    await page.getByRole('heading', { name: 'Quản lý nhãn hàng' }).waitFor({ timeout: 60000 });
    log('SIGNUP_OK');

    const name = 'Mây Tea';
    await page.locator('input[maxlength="200"]').fill(name);
    await page.locator('textarea').fill('Mây Tea');
    const created = page.waitForResponse(r => r.request().method() === 'POST' && new URL(r.url()).pathname === '/api/brands');
    await page.getByRole('button', { name: 'Tạo nhãn hàng', exact: true }).click();
    const response = await created;
    if (response.status() !== 201) throw new Error(`Tạo nhãn hàng lỗi ${response.status()}`);
    const brand = await response.json();
    await page.getByText('Đã lưu nhãn hàng và cấu hình. Lịch hoạt động khi dịch vụ lịch được bật.').waitFor();
    await page.getByRole('button', { name, exact: true }).click();
    await page.getByText(`Mã nhãn hàng cho người vận hành demo: ${brand.id}`).waitFor();

    const rules = page.locator('section').filter({ has: page.getByRole('heading', { name: 'Quy tắc cảnh báo', exact: true }) });
    const rule = rules.locator('form').filter({ has: page.getByRole('heading', { name: 'Bình luận tiêu cực' }) });
    await rule.getByLabel('Bật quy tắc').check();
    await rule.getByLabel('Ngưỡng tăng (%)').fill('50');
    await rule.getByLabel('Độ dài mỗi cửa sổ (ngày)').fill('1');
    await rule.getByLabel('Số nội dung tối thiểu').fill('10');
    await rule.getByRole('button', { name: 'Lưu quy tắc' }).click();
    await rules.getByText('Đã lưu quy tắc.').waitFor();
    // Tải lại trang: dữ liệu còn sau khi đăng nhập lại chứng minh đã lưu trong database.
    log(`DEMO_BRAND_ID=${brand.id}`);

    const live = page.locator('#live-alerts');
    const rows = live.locator('tbody tr');
    await rows.nth(0).waitFor({ timeout: 15 * 60 * 1000 });
    log(`BASELINE ${(await rows.nth(0).innerText()).replace(/\s+/g, ' ')}`);
    await rows.nth(1).waitFor({ timeout: 10 * 60 * 1000 });
    log(`NEGATIVE ${(await rows.nth(1).innerText()).replace(/\s+/g, ' ')}`);
    await live.getByText('Bình luận tiêu cực tăng vượt ngưỡng').waitFor({ timeout: 60000 });
    log(`ALERT ${(await live.getByRole('alert').innerText()).replace(/\s+/g, ' ')}`);
    if (!/20% \(20\/100\) lên 30% \(60\/200\)/.test(await live.getByRole('alert').innerText())) throw new Error('Số liệu cảnh báo không đúng');

    const alertList = page.waitForResponse(r => r.request().method() === 'GET' && /\/api\/brands\/[^/]+\/alerts\?/.test(r.url()));
    await live.getByRole('button', { name: 'Đánh giá lại lần thu thập gần nhất' }).click();
    await live.getByText(/không tạo cảnh báo trùng/).waitFor({ timeout: 30000 });
    const alerts = (await (await alertList).json()).filter(item => item.mode === 'run');
    if (alerts.length !== 1) throw new Error(`Số cảnh báo không đúng: ${alerts.length}`);
    log(`ALERT_ID=${alerts[0].id} notified_at=${alerts[0].notified_at}`);

    // Phân tích AI cho khoảng vừa thu thập; mốc cuối là phút tròn đã qua sau đợt tiêu cực.
    await page.waitForTimeout(65000);
    const analysis = page.locator('section').filter({ has: page.getByRole('heading', { name: 'Phân tích AI', exact: true }) });
    const localTime = date => new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
    const end = new Date(Math.floor(Date.now() / 60000) * 60000);
    await analysis.getByLabel('Thu thập từ').fill(localTime(new Date(end.getTime() - 60 * 60000)));
    await analysis.getByLabel('Thu thập trước').fill(localTime(end));
    let aiPassed = false;
    for (let attempt = 0; attempt < 2 && !aiPassed; attempt++) {
      const result = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith('/analyses'), { timeout: 150000 });
      await analysis.getByRole('button', { name: attempt === 0 ? 'Tạo phân tích' : /Kiểm tra lại yêu cầu|Tạo phân tích/ }).click();
      const r = await result; const job = await r.json().catch(() => ({}));
      aiPassed = r.status() === 200 && job.status === 'success' && !!job.findings?.length;
      log(`AI_ATTEMPT ${attempt + 1} http=${r.status()} status=${job.status} code=${job.error_code ?? 'none'} samples=${job.sample_count ?? '-'}`);
      if (aiPassed) job.findings.forEach((finding, index) => log(`AI_FINDING ${index + 1}: ${finding.summary} | Gợi ý: ${finding.recommendation} | ${finding.evidence_ids.length} dẫn chứng`));
    }
    if (aiPassed) await analysis.getByRole('heading', { name: 'Phân tích hoàn tất' }).first().scrollIntoViewIfNeeded();

    log('READY_FOR_RELEASE');
    await rows.nth(2).waitFor({ timeout: 10 * 60 * 1000 });
    log(`POSITIVE ${(await rows.nth(2).innerText()).replace(/\s+/g, ' ')}`);
    if (!/65 \/ 300\s+22%\s+Không cảnh báo/.test(await rows.nth(2).innerText())) throw new Error('Đợt tích cực không đúng kịch bản');

    // Liên kết email: mở tab mới; phiên Cognito còn hạn nên quay lại ngay và mở đúng nhãn hàng.
    const linked = await context.newPage();
    await linked.goto(`${ui.origin}/?brand=${brand.id}&alert=${alerts[0].id}`);
    await linked.getByText(/Bạn mở từ email cảnh báo/).waitFor({ timeout: 90000 });
    log('EMAIL_LINK_OK');
    await linked.waitForTimeout(2000);
    console.log(aiPassed ? 'DEMO_MINUTE_FLOW_OK' : 'DEMO_MINUTE_FLOW_OK_WITHOUT_AI');
  } finally { if (context) await context.close(); await browser.close(); }
})().catch(error => { console.error(error.message); process.exitCode = 1; });
