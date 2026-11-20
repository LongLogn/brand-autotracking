// Kiểm tra trang đăng ký của Cognito hiển thị; không tạo tài khoản hay gửi email.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE);
(async () => {
  const browser = await chromium.launch({ executablePath: process.env.TEST_BROWSER, headless: true });
  try {
    const page = await browser.newPage();
    await page.goto(process.env.TEST_UI_BASE);
    await page.getByRole('button', { name: 'Tạo tài khoản' }).click();
    await page.waitForURL('https://*.amazoncognito.com/signup?**', { timeout: 30000 });
    await page.locator('input[name="username"]:visible, input[name="email"]:visible').first().waitFor({ timeout: 30000 });
    console.log('Cognito signup page displayed');
  } finally { await browser.close(); }
})().catch((error) => { console.error(error.message); process.exitCode = 1; });
