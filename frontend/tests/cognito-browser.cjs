// Chỉ chạy khi backend dùng Cognito thật và DB thử nghiệm; tài khoản do harness tạo/xóa.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE);
const assert = require('node:assert/strict');
const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const apiBase = process.env.TEST_AWS_API_BASE || 'http://127.0.0.1:18039';

(async () => {
  const browser = await chromium.launch({ executablePath: process.env.TEST_BROWSER, headless: true });
  try {
    async function signIn(username, password) {
      const context = await browser.newContext();
      const page = await context.newPage();
      let token = '';
      page.on('request', (request) => { if (request.url().startsWith(`${apiBase}/brands`)) token = request.headers().authorization || token; });
      await page.goto(process.env.TEST_UI_BASE);
      await page.getByRole('button', { name: 'Đăng nhập với Cognito' }).click();
      try {
        await page.locator('input[name="username"]:visible').first().waitFor({ timeout: 30000 });
      } catch (error) {
        console.error(`Cognito login form unavailable at ${page.url()}: ${await page.locator('body').innerText()}`);
        throw error;
      }
      await page.locator('input[name="username"]:visible').first().fill(username);
      await page.locator('input[name="password"]:visible').first().fill(password);
      await page.locator('button[type="submit"]:visible, input[type="submit"]:visible').first().click();
      await page.getByRole('heading', { name: 'Quản lý nhãn hàng' }).waitFor({ timeout: 30000 });
      assert.ok(token.startsWith('Bearer '));
      return { page, token };
    }
    const { page, token } = await signIn(process.env.TEST_COGNITO_USERNAME, process.env.TEST_COGNITO_PASSWORD);
    assert.equal(new URL(page.url()).search, '');
    assert.equal(await page.evaluate(() => Object.keys(sessionStorage).filter((x) => x.includes('oauth')).length), 0);
    const createResponse = page.waitForResponse((response) => response.request().method() === 'POST' && response.url() === `${apiBase}/brands`);
    const brandName = process.env.TEST_TRACKING_ITEM1 === '1' ? 'Item 1 tracking verification' : 'Cognito isolation test';
    await page.locator('input[maxlength="200"]').fill(brandName);
    await page.locator('textarea').fill(process.env.TEST_TRACKING_QUERY || 'coffee');
    await page.getByRole('button', { name: 'Tạo nhãn hàng', exact: true }).click();
    const created = await (await createResponse).json();
    await page.getByText('Đã lưu nhãn hàng và cấu hình. Lịch hoạt động khi dịch vụ lịch được bật.').waitFor();
    if (process.env.TEST_ANALYSIS_FIXTURE_FUNCTION) {
      const invokeFixture = (kind) => {
        const responseFile = path.join(os.tmpdir(), `brand-ai-fixture-${crypto.randomUUID()}.json`);
        try {
          const result = JSON.parse(execFileSync('aws', ['lambda', 'invoke', '--function-name', process.env.TEST_ANALYSIS_FIXTURE_FUNCTION,
            '--cli-binary-format', 'raw-in-base64-out', '--payload', JSON.stringify({ brand_id: created.id, kind }), responseFile,
            '--output', 'json'], { encoding: 'utf8', env: process.env }));
          assert.equal(result.FunctionError, undefined);
          return JSON.parse(fs.readFileSync(responseFile, 'utf8'));
        } finally { fs.rmSync(responseFile, { force: true }); }
      };
      const fixture = invokeFixture('analysis');
      await page.getByRole('button', { name: brandName, exact: true }).click();
      const analysis = page.locator('section').filter({ has: page.getByRole('heading', { name: 'Phân tích AI', exact: true }) });
      await analysis.getByLabel('Thu thập từ').fill('2026-01-01T00:00');
      await analysis.getByLabel('Thu thập trước').fill('2026-01-02T00:00');
      const analysisResponse = page.waitForResponse((response) => response.request().method() === 'POST' && response.url().endsWith('/analyses'));
      await analysis.getByRole('button', { name: 'Tạo phân tích' }).click();
      const result = await analysisResponse;
      assert.equal(result.status(), 200);
      const job = await result.json();
      assert.equal(job.status, 'success');
      assert.ok(job.findings.length > 0);
      assert.ok(job.findings.every((finding) => finding.evidence_ids.includes(`post:${fixture.post_id}`)));
      await analysis.getByRole('link', { name: `post:${fixture.post_id}` }).waitFor();
      console.log('AWS analysis through browser, API Gateway and Bedrock passed with synthetic evidence');
      assert.deepEqual(invokeFixture('alert'), { previous: 10, current: 15 });
      const alerts = page.locator('section').filter({ has: page.getByRole('heading', { name: 'Quy tắc cảnh báo', exact: true }) });
      const rule = alerts.locator('form').filter({ has: page.getByRole('heading', { name: 'Bài viết tiêu cực' }) });
      await rule.getByLabel('Bật quy tắc').check();
      await rule.getByLabel('Ngưỡng tăng (%)').fill('50');
      await rule.getByLabel('Độ dài mỗi cửa sổ (ngày)').fill('1');
      await rule.getByLabel('Số nội dung tối thiểu').fill('5');
      await rule.getByRole('button', { name: 'Lưu quy tắc' }).click();
      await alerts.getByText('Đã lưu quy tắc.').waitFor();
      const firstEvaluation = page.waitForResponse((response) => response.request().method() === 'POST' && response.url().endsWith('/alert-rules/post/evaluate'));
      await rule.getByRole('button', { name: 'Đánh giá cửa sổ đã hoàn tất' }).click();
      const firstAlert = await (await firstEvaluation).json();
      await alerts.getByText('Đã có cảnh báo cho cửa sổ này. Kỳ trước: 10; kỳ này: 15.').waitFor();
      await alerts.locator('li').first().waitFor();
      assert.equal(await alerts.locator('li').count(), 1);
      const secondEvaluation = page.waitForResponse((response) => response.request().method() === 'POST' && response.url().endsWith('/alert-rules/post/evaluate'));
      const alertHistory = page.waitForResponse((response) => response.request().method() === 'GET' && /\/alerts(?:\?|$)/.test(response.url()));
      await rule.getByRole('button', { name: 'Đánh giá cửa sổ đã hoàn tất' }).click();
      const secondAlert = await (await secondEvaluation).json();
      assert.equal(secondAlert.alert.id, firstAlert.alert.id);
      const history = await (await alertHistory).json();
      assert.equal(history.length, 1);
      await alerts.getByText('Đã có cảnh báo cho cửa sổ này. Kỳ trước: 10; kỳ này: 15.').waitFor();
      assert.equal(await alerts.locator('li').count(), 1);
      console.log('AWS alert through browser and API Gateway passed with synthetic 10-to-15 evidence');
    }
    if (process.env.TEST_TRACKING_ITEM1 === '1') {
      const request = (path, options = {}) => page.evaluate(async ({ apiBase, path, token, options }) => {
        const response = await fetch(`${apiBase}${path}`, { ...options, headers: { Authorization: token, ...(options.headers || {}) } });
        return { status: response.status, body: await response.json() };
      }, { apiBase, path, token, options });
      async function runAndRead() {
        const queued = await request(`/brands/${created.id}/runs`, { method: 'POST' });
        assert.equal(queued.status, 202);
        const runId = queued.body.id;
        let detail;
        for (let attempt = 0; attempt < 90; attempt++) {
          await new Promise((resolve) => setTimeout(resolve, 2000));
          detail = await request(`/brands/${created.id}/runs/${runId}`);
          if (['success', 'partial', 'failed', 'skipped'].includes(detail.body.status)) break;
        }
        assert.ok(detail && ['success', 'partial', 'failed', 'skipped'].includes(detail.body.status));
        const posts = await request(`/brands/${created.id}/runs/${runId}/mentions`);
        const comments = posts.body[0] ? await request(`/brands/${created.id}/runs/${runId}/mentions/${posts.body[0].id}/comments`) : { body: [] };
        return { runId, status: detail.body.status, error: detail.body.error_code,
                 postId: posts.body[0]?.id || null, sourceId: posts.body[0]?.source_id || null,
                 posts: posts.body.length, comments: comments.body.length };
      }
      if (process.env.TEST_AWS_RECOVERY_ITEM1 === '1') {
        const queued = await request(`/brands/${created.id}/runs`, { method: 'POST' });
        assert.equal(queued.status, 202);
        console.log(`ITEM1_QUEUED ${queued.body.id}`);
        let runs = [];
        for (let attempt = 0; attempt < 120; attempt++) {
          await new Promise((resolve) => setTimeout(resolve, 2000));
          const response = await request(`/brands/${created.id}/runs`);
          runs = response.body;
          if (runs.some((run) => run.status === 'failed' && run.error_code === 'worker_timeout') &&
              runs.some((run) => run.status === 'success')) break;
        }
        const failed = runs.find((run) => run.status === 'failed' && run.error_code === 'worker_timeout');
        const recovered = runs.find((run) => run.status === 'success');
        assert.ok(failed && recovered);
        const detail = await request(`/brands/${created.id}/runs/${recovered.id}`);
        const posts = await request(`/brands/${created.id}/runs/${recovered.id}/mentions`);
        console.log(`ITEM1_RECOVERY ${JSON.stringify({ failedId: failed.id, recoveredId: recovered.id,
          recoveredFrom: detail.body.config_snapshot?.recovered_from || null, posts: posts.body.length })}`);
      } else {
        const first = await runAndRead();
        const second = await runAndRead();
        console.log(`ITEM1_RESULT ${JSON.stringify({ first, second, sameSourcePost: Boolean(first.sourceId && first.sourceId === second.sourceId) })}`);
      }
    }
    // Ép đồng hồ trang tiến gần hạn để thử refresh thật mà không chờ một giờ.
    await page.evaluate(() => { const originalNow = Date.now; Date.now = () => originalNow() + 3600_000; });
    const refreshResponse = page.waitForResponse((response) => response.url().includes('/oauth2/token') && response.request().method() === 'POST');
    await page.getByRole('button', { name: 'Tải lại', exact: true }).click();
    const refreshed = await refreshResponse;
    assert.equal(refreshed.status(), 200);
    assert.equal(new URLSearchParams(refreshed.request().postData()).get('grant_type'), 'refresh_token');
    await page.getByRole('button', { name: brandName, exact: true }).waitFor();
    const second = await signIn(process.env.TEST_COGNITO_USERNAME_B, process.env.TEST_COGNITO_PASSWORD_B);
    const isolation = await second.page.evaluate(async ({ token, id, apiBase, checkAnalysis }) => {
      const base = `${apiBase}/brands`;
      const headers = { Authorization: token, 'Content-Type': 'application/json' };
      const list = await fetch(base, { headers });
      const items = await list.json();
      const read = await fetch(`${base}/${id}/tracking`, { headers });
      const write = await fetch(`${base}/${id}`, { method: 'PUT', headers, body: JSON.stringify({ name: 'unauthorized' }) });
      const analysis = checkAnalysis ? await fetch(`${base}/${id}/analyses`, { headers }) : null;
      return { visible: items.some((item) => item.id === id), read: read.status, write: write.status,
        ...(analysis ? { analysis: analysis.status } : {}) };
    }, { token: second.token, id: created.id, apiBase, checkAnalysis: Boolean(process.env.TEST_ANALYSIS_FIXTURE_FUNCTION) });
    assert.deepEqual(isolation, { visible: false, read: 404, write: 404,
      ...(process.env.TEST_ANALYSIS_FIXTURE_FUNCTION ? { analysis: 404 } : {}) });
    if (process.env.TEST_DELETE_BRAND === '1') {
      const denied = await second.page.evaluate(async ({ apiBase, token, id }) => {
        const response = await fetch(`${apiBase}/brands/${id}`, { method: 'DELETE', headers: { Authorization: token } });
        return response.status;
      }, { apiBase, token: second.token, id: created.id });
      assert.equal(denied, 404);
      await page.getByRole('button', { name: brandName, exact: true }).click();
      page.once('dialog', (dialog) => dialog.accept());
      const deletion = page.waitForResponse((response) => response.request().method() === 'DELETE' && response.url() === `${apiBase}/brands/${created.id}`);
      await page.getByRole('button', { name: 'Xóa vĩnh viễn' }).click();
      assert.equal((await deletion).status(), 200);
      await page.getByText('Đã xóa nhãn hàng và dữ liệu liên quan.').waitFor();
      assert.equal(await page.getByRole('button', { name: brandName, exact: true }).count(), 0);
      console.log('AWS hosted delete confirmation and cross-account rejection passed');
    }
    await second.page.getByRole('button', { name: 'Ngắt kết nối' }).click();
    await second.page.getByRole('button', { name: 'Đăng nhập với Cognito' }).click();
    await second.page.locator('input[name="username"]:visible').first().waitFor({ timeout: 30000 });
    console.log('Cognito login, token refresh, cross-account isolation and managed-login logout passed');
  } finally { await browser.close(); }
})().catch((error) => { console.error(error.message); process.exitCode = 1; });
