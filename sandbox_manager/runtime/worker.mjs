/** Fixed OCI entrypoint. Never execute this with untrusted inputs on the host. */
import fs from 'node:fs';
import http from 'node:http';
import crypto from 'node:crypto';
import {spawn} from 'node:child_process';

const MAX = 20000;
const request = JSON.parse(fs.readFileSync('/request.json', 'utf8'));
const allowed = new Set(['javascript', 'typescript', 'browser']);
if (!allowed.has(request.profile) || process.getuid() === 0) throw Error('Invalid profile or root worker');
const safePath = name => typeof name === 'string' && /^[A-Za-z0-9_./-]{1,180}$/.test(name)
  && !name.startsWith('/') && name.split('/').every(p => p && !['.', '..', '.env', '.git'].includes(p));
let bytes = 0;
for (const [name, text] of Object.entries(request.files ?? {})) {
  if (!safePath(name) || typeof text !== 'string' || text.includes('\0')) throw Error('Invalid source');
  bytes += Buffer.byteLength(text);
}
if (bytes > MAX || Object.keys(request.files ?? {}).length > 50) throw Error('Source budget');
let logs = '', exitCode = 0;
const append = value => { if (Buffer.byteLength(logs) + Buffer.byteLength(value) > 32000) throw Error('Log budget'); logs += value; process.stdout.write(JSON.stringify({event:'progress',message:value})+'\n'); };
if (request.profile !== 'browser') {
  const suffix = request.profile === 'javascript' ? '.js' : '.ts';
  if (!safePath(request.entrypoint) || !request.entrypoint.endsWith(suffix)
      || !Object.hasOwn(request.files, request.entrypoint)) throw Error('Invalid entrypoint');
  const args = ['--max-old-space-size=256'];
  if (request.profile === 'typescript') args.push('--experimental-strip-types');
  args.push('/work/' + request.entrypoint);
  const child = spawn(process.execPath, args, {cwd:'/work', env:{HOME:'/tmp', LANG:'C.UTF-8'}, stdio:['ignore','pipe','pipe']});
  let logBudgetExceeded = false;
  const timer = setTimeout(() => child.kill('SIGKILL'), 15000);
  for (const stream of [child.stdout, child.stderr]) stream.on('data', chunk => {
    try { append(chunk.toString('utf8')); } catch { logBudgetExceeded = true; child.kill('SIGKILL'); }
  });
  exitCode = await new Promise((resolve, reject) => {child.once('error', reject); child.once('close', code => resolve(code ?? 1));});
  clearTimeout(timer);
  if (logBudgetExceeded) {
    exitCode = 1; logs = logs.slice(0, 30000) + '\nExecution output budget exceeded.\n';
    process.stdout.write(JSON.stringify({event:'progress',message:'Execution output budget exceeded.\n'})+'\n');
  }
} else {
  // Offline controlled-site profile: no external navigation or form submission.
  const actions = request.actions;
  if (!Array.isArray(actions) || !actions.length || actions.length > 12) throw Error('Action budget');
  const server = http.createServer((req, res) => {
    if (!['GET','HEAD'].includes(req.method)) {res.writeHead(405); res.end(); return;}
    const pathname = new URL(req.url, 'http://localhost').pathname;
    const name = pathname === '/' ? 'index.html' : pathname.slice(1);
    if (!safePath(name) || !Object.hasOwn(request.files, name)) {res.writeHead(404); res.end(); return;}
    const type = name.endsWith('.html') ? 'text/html' : name.endsWith('.js') ? 'text/javascript'
      : name.endsWith('.css') ? 'text/css' : 'text/plain';
    res.setHeader('Content-Type', type + '; charset=utf-8');
    res.setHeader('Content-Security-Policy', "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; form-action 'none'; object-src 'none'; frame-src 'none'");
    if (req.method === 'HEAD') res.end(); else res.end(request.files[name]);
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const origin = 'http://127.0.0.1:' + server.address().port;
  let browser;
  try {
    const {chromium} = await import('playwright');
    // Never fall back to --no-sandbox when kernel support is unavailable.
    browser = await chromium.launch({headless:true, chromiumSandbox:true});
    const context = await browser.newContext({acceptDownloads:true, serviceWorkers:'block', viewport:{width:640,height:480}});
    await context.route('**/*', route => {
      const req = route.request(); const url = new URL(req.url());
      return url.origin === origin && ['GET','HEAD'].includes(req.method())
        ? route.continue() : route.abort('blockedbyclient');
    });
    const page = await context.newPage();
    page.setDefaultTimeout(3000);
    await page.goto(origin);
    let shots = 0;
    for (const action of actions) {
      const target = action.target ?? '';
      switch (action.action) {
        case 'navigate':
          if (!target.startsWith('/') || target.startsWith('//') || /[%\\\x00-\x1f]/.test(target)
              || target.split('/').includes('..') || new URL(target, origin).origin !== origin) throw Error('Unsafe navigation');
          await page.goto(origin + target); break;
        case 'inspect': append((await page.locator('body').innerText()).slice(0, 4000) + '\n'); break;
        case 'type': await page.locator(target).fill(String(action.text ?? '').slice(0, 2000)); break;
        case 'click': await page.locator(target).click(); break;
        case 'screenshot':
          if (++shots > 2) throw Error('Screenshot budget');
          await page.screenshot({path:'/out/screenshot-' + shots + '.png'}); break;
        case 'download': {
          const [download] = await Promise.all([page.waitForEvent('download'),page.locator(target).click()]);
          // Fixed output name; never trust a suggested filename or content type.
          await download.saveAs('/out/result.txt'); break;
        }
        default: throw Error('Unsupported browser action');
      }
      append(JSON.stringify({event:'step.completed', action:action.action}) + '\n');
    }
  } finally {
    if (browser) await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
}
// Bounded output is untrusted. The manager must independently validate it.
const artifacts = {};
let total = 0;
for (const name of ['result.txt','result.json','result.csv','result.md','screenshot-1.png','screenshot-2.png']) {
  const file = '/out/' + name;
  if (!fs.existsSync(file)) continue;
  const stat = fs.lstatSync(file);
  if (!stat.isFile() || stat.isSymbolicLink() || stat.size > MAX) throw Error('Invalid artifact');
  const data = fs.readFileSync(file);
  if ((total += data.length) > MAX) throw Error('Artifact budget');
  artifacts[name] = {base64:data.toString('base64'), size:data.length, sha256:crypto.createHash('sha256').update(data).digest('hex')};
}
console.log(JSON.stringify({event:'result',exit_code:exitCode, stdout:logs, artifacts}));
process.exitCode = exitCode;
