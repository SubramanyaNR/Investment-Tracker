// End-to-end UI test against the PRODUCTION frontend in a real headless browser.
// Self-cleaning: every asset it creates is prefixed and deleted at the end.
// BASE_URL defaults to the local prod server; override via env for the VM IP.
import { chromium } from 'playwright';

const BASE = process.env.BASE_URL || 'http://127.0.0.1:3000';
const PREFIX = 'SKILLTEST';
let pass = 0, fail = 0;
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
function rec(name, ok, detail = '') {
  if (ok) pass++; else fail++;
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? '  — ' + detail : ''}`);
}

const browser = await chromium.launch({ headless: true });
const page = await browser.newContext().then(c => c.newPage());
const consoleErrors = [], apiFailures = [];
page.on('console', m => { if (m.type() === 'error') consoleErrors.push(m.text()); });
page.on('pageerror', e => consoleErrors.push('PAGEERROR: ' + e.message));
page.on('response', r => { if (r.url().includes('/api/') && r.status() >= 400) apiFailures.push(`${r.status()} ${r.url()}`); });
page.on('dialog', d => d.accept());

const type = async (v) => { await page.getByRole('combobox').first().selectOption(v); await sleep(200); };
const holdings = async () => { await page.getByRole('tab', { name: /^Holdings/ }).click(); await sleep(300); };
const addBtn = () => page.getByRole('button', { name: /^Add(ing)?/ });
const fillName = (n) => page.getByPlaceholder(/e\.g\. Bitcoin/).fill(n);
const waitRow = (n, t = 15000) => page.getByText(n, { exact: true }).first().waitFor({ timeout: t });

try {
  // 1. Dashboard
  await page.goto(BASE, { waitUntil: 'networkidle', timeout: 30000 });
  await page.getByText('Net Worth').first().waitFor({ timeout: 15000 });
  rec('Dashboard loads (KPIs)', await page.getByText('Profit / Loss').first().isVisible());

  // 2. Theme toggle
  await page.getByRole('button', { name: 'Light mode' }).click(); await sleep(150);
  const light = await page.evaluate(() => document.documentElement.getAttribute('data-theme'));
  await page.getByRole('button', { name: 'Dark mode' }).click(); await sleep(150);
  const dark = await page.evaluate(() => document.documentElement.getAttribute('data-theme'));
  rec('Theme toggle', light === 'light' && dark === 'dark');

  // 3. Asset-type switching
  await holdings();
  await type('CRYPTO'); const c = await page.getByPlaceholder('0.05').isVisible();
  await type('FD');     const f = await page.getByPlaceholder('100000').isVisible();
  await type('MUTUAL_FUND'); const m = await page.getByPlaceholder('50000').isVisible();
  rec('Asset-type switching', c && f && m);

  // 4. MF search + add (parag = not a held scheme; safe)
  await type('MUTUAL_FUND');
  await page.locator('.selector-trigger').first().click();
  await page.getByPlaceholder(/Type 3\+ chars/).fill('parag');
  await page.locator('button[role="option"]').first().waitFor({ timeout: 20000 });
  rec('MF search returns results', (await page.locator('button[role="option"]').count()) > 0);
  await page.locator('button[role="option"]').first().click();
  await sleep(400);
  await fillName(`${PREFIX} MF`);
  await page.getByPlaceholder('50000').fill('50000');
  const nav = page.getByPlaceholder('45.23');
  await page.waitForFunction(() => { const e = document.querySelector('input[placeholder="45.23"]'); return e && !e.disabled; }, { timeout: 15000 });
  if (!(await nav.inputValue())) await nav.fill('45.23');
  await addBtn().click(); await waitRow(`${PREFIX} MF`);
  rec('Add Mutual Fund', true);

  // 5. Crypto add (bitcoin = not held; safe)
  await type('CRYPTO');
  await fillName(`${PREFIX} BTC`);
  await page.locator('.selector-trigger').first().click();
  await page.getByPlaceholder('Search coins…').fill('bitcoin');
  await page.locator('button[role="option"]').first().waitFor({ timeout: 20000 });
  await page.locator('button[role="option"]').first().click();
  await page.getByPlaceholder('0.05').fill('0.01');
  await page.getByPlaceholder('9200000').fill('5000000');
  await addBtn().click(); await waitRow(`${PREFIX} BTC`);
  rec('Add Crypto', true);

  // 6. FD / RD / PPF
  for (const [t, name, prin, rate, date] of [
    ['FD', `${PREFIX} FD`, '100000', '7.5', '2025-01-01'],
    ['RD', `${PREFIX} RD`, '5000', '7.0', '2025-01-01'],
    ['PPF', `${PREFIX} PPF`, '150000', '7.1', '2024-04-01'],
  ]) {
    await type(t);
    await fillName(name);
    await page.getByPlaceholder(t === 'RD' ? '5000' : '100000').fill(prin);
    await page.getByPlaceholder('7.5').fill(rate);
    await page.locator('input[type="date"]').first().fill(date);
    await addBtn().click(); await waitRow(name);
  }
  rec('Add FD/RD/PPF', true);

  // 7. List + refresh + sell + transactions
  const present = await Promise.all(['MF', 'BTC', 'FD', 'RD', 'PPF'].map(s => page.getByText(`${PREFIX} ${s}`, { exact: true }).first().isVisible()));
  rec('Asset list shows all', present.every(Boolean), present.join(','));

  await page.getByRole('button', { name: 'Refresh live prices' }).click();
  await page.waitForFunction(() => { const b = document.querySelector('.btn-refresh'); return b && !b.disabled; }, { timeout: 60000 });
  await sleep(1000);
  rec('Valuation refresh (no error banner)', !(await page.locator('.error-banner').isVisible().catch(() => false)));

  await holdings();
  await page.getByLabel('Sell quantity').fill('0.005');
  await page.getByRole('button', { name: 'Sell', exact: true }).click();
  await sleep(2500);
  rec('Sell crypto (no error)', !(await page.locator('.error-banner').isVisible().catch(() => false)));

  await page.getByRole('tab', { name: /^Transactions/ }).click(); await sleep(400);
  rec('Transactions populated', await page.getByText('Transaction History').isVisible().catch(() => false));

  // 8. Cleanup — delete everything this run created
  await holdings();
  for (let i = 0; i < 12; i++) {
    const btn = page.locator(`button[aria-label^="Remove ${PREFIX}"]`).first();
    if (await btn.count() === 0) break;
    await btn.click({ force: true });
    await sleep(1500);
  }
  rec('Cleanup (no SKILLTEST assets remain)', (await page.locator(`button[aria-label^="Remove ${PREFIX}"]`).count()) === 0);

} catch (err) {
  rec('UNCAUGHT', false, err.message);
} finally {
  console.log('\nconsole errors: ' + (consoleErrors.length ? consoleErrors.join(' | ') : 'none'));
  console.log('api failures:   ' + (apiFailures.length ? apiFailures.join(' | ') : 'none'));
  console.log(`\n=== ${pass} passed, ${fail} failed ===`);
  await browser.close();
  process.exit(fail > 0 ? 1 : 0);
}
