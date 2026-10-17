// Kleine testharnas: start chromium headless, opent de game en maakt screenshots.
// Gebruik: node tools/cdp.mjs <url> <uitmap> [script.json]
import { spawn } from 'node:child_process';
import { writeFileSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const [url, outDir, stepsJson] = process.argv.slice(2);
const steps = stepsJson ? JSON.parse(stepsJson) : [{ wait: 3000 }, { shot: 'a' }];
const prof = mkdtempSync(join(outDir, 'prof-'));
const port = 9300 + Math.floor(Math.random() * 500);
const chrome = spawn('chromium', ['--headless=new', '--no-sandbox', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist',
  '--disable-extensions', '--window-size=1280,800', `--user-data-dir=${prof}`, `--remote-debugging-port=${port}`, 'about:blank'], { stdio: 'ignore' });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let ws;
for (let i = 0; i < 50; i++) {
  try { const list = await (await fetch(`http://127.0.0.1:${port}/json`)).json(); const page = list.find((t) => t.type === 'page'); if (page) { ws = new WebSocket(page.webSocketDebuggerUrl); break; } } catch {}
  await sleep(200);
}
await new Promise((r) => ws.addEventListener('open', r));
let id = 0; const pending = new Map();
ws.addEventListener('message', (ev) => {
  const m = JSON.parse(ev.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
  if (m.method === 'Runtime.consoleAPICalled') console.log('[console.' + m.params.type + ']', m.params.args.map((a) => a.value ?? a.description).join(' ').slice(0, 300));
  if (m.method === 'Runtime.exceptionThrown') console.log('[exception]', JSON.stringify(m.params.exceptionDetails).slice(0, 800));
});
const send = (method, params = {}) => new Promise((r) => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
await send('Runtime.enable'); await send('Page.enable');
if (process.env.VIEWPORT) { // bijvoorbeeld VIEWPORT=1200x630x2 voor een social image
  const [w, h, dpr] = process.env.VIEWPORT.split('x').map(Number);
  await send('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: dpr, mobile: false });
}
if (process.env.MOBILE) { // bijvoorbeeld MOBILE=390x844x3
  const [w, h, dpr] = process.env.MOBILE.split('x').map(Number);
  await send('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: dpr, mobile: true });
  await send('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 5 });
}
await send('Page.navigate', { url });
for (const s of steps) {
  if (s.wait) await sleep(s.wait);
  if (s.eval) { const r = await send('Runtime.evaluate', { expression: s.eval, returnByValue: true, awaitPromise: true }); console.log('[eval]', JSON.stringify(r.result?.result?.value ?? r.result?.exceptionDetails ?? r).slice(0, 600)); }
  if (s.until) { const t0 = Date.now(); for (;;) { const r = await send('Runtime.evaluate', { expression: s.until, returnByValue: true }); if (r.result?.result?.value) break; if (Date.now() - t0 > (s.timeout || 60000)) { console.log('[until] timeout', s.until); break; } await sleep(500); } }
  if (s.shot) { const r = await send('Page.captureScreenshot', { format: 'png' }); writeFileSync(join(outDir, s.shot + '.png'), Buffer.from(r.result.data, 'base64')); console.log('[shot]', s.shot); }
}
ws.close(); chrome.kill('SIGKILL');
process.exit(0);
