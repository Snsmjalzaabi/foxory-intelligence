import {test,expect} from '@playwright/test';

// Keep this shared-server suite below the real 180/minute per-IP API limit.
let nextAPIRequest=0;
let apiQueue:Promise<void>=Promise.resolve();

test.beforeEach(async({page})=>{
 await page.route('**/api/**',async route=>{
  const queued=apiQueue.then(async()=>{const delay=Math.max(0,nextAPIRequest-Date.now());if(delay)await new Promise<void>(resolve=>setTimeout(resolve,delay));nextAPIRequest=Date.now()+400;});
  apiQueue=queued.catch(()=>{});await queued;await route.continue();
 });
 await page.goto('/');
 await expect(page.getByRole('button',{name:/Sign in|Create administrator/})).toBeVisible();
 if(test.info().title.startsWith('chat streams'))await page.screenshot({path:'test-results/core-login.png',fullPage:true});
 if(await page.getByLabel('Workspace bootstrap token').isVisible())await page.getByLabel('Workspace bootstrap token').fill('e2e-only-token-with-at-least-24-chars');
 await page.getByLabel('Username',{exact:true}).fill('e2e-owner');
 await page.getByLabel('Password',{exact:true}).fill('e2e-owner-password-123');
 await page.getByRole('button',{name:/Sign in|Create administrator/}).click();
 await expect(page.getByRole('heading',{name:'What will you build today?'})).toBeVisible({timeout:20000});
});

test('chat streams, persists, regenerates and exports through the real HTTP adapter',async({page})=>{
 await page.locator('nav').getByRole('button',{name:'Settings',exact:true}).click();
 await page.getByRole('combobox',{name:'Response budget',exact:true}).selectOption('128');
 await page.locator('nav').getByRole('button',{name:'Chat',exact:true}).click();
 await page.getByLabel('Message FOXORY').fill('Explain local ownership');
 const sent=page.waitForRequest(r=>r.url().endsWith('/chat')&&r.method()==='POST');
 await page.getByRole('button',{name:'Send message'}).click();
 expect((await sent).postDataJSON().max_output).toBe(128);
 await expect(page.locator('.message.assistant')).toContainText('Test fixture response: Explain local ownership');
 await expect(page.getByLabel('Regenerate last response')).toBeVisible();
 await page.getByLabel('Regenerate last response').click();
 await expect(page.getByLabel('Regenerate last response')).toBeVisible();
 await expect(page.locator('.message')).toHaveCount(2);
 await page.reload();
 await page.locator('.history-row').filter({hasText:'Explain local ownership'}).first().locator('button').first().click();
 await expect(page.locator('.message.assistant')).toContainText('Test fixture response');
 const download=page.waitForEvent('download');await page.getByLabel('Export conversation').click();
 expect((await download).suggestedFilename()).toBe('conversation.md');
 await page.screenshot({path:'test-results/chat-desktop.png',fullPage:true});
});

test('document upload, grounded question and validation errors',async({page})=>{
 await page.locator('nav').getByRole('button',{name:'Documents',exact:true}).click();
 await page.locator('input[type=file]').setInputFiles({name:'quarter.txt',mimeType:'text/plain',buffer:Buffer.from('Quarter revenue was 100 units.')});
 await expect(page.getByRole('heading',{name:'quarter.txt',exact:true})).toBeVisible({timeout:20000});
 await page.getByLabel('Document question').fill('What was revenue?');
 await page.getByRole('button',{name:'Ask documents'}).click();
 await expect(page.locator('.document-answer')).toContainText('Extractive evidence report');
 await expect(page.locator('.document-answer')).toContainText('Quarter revenue was 100 units');
 await expect(page.locator('.document-answer')).toContainText('quarter.txt');
 await page.screenshot({path:'test-results/core-documents.png',fullPage:true});
 const rejected=page.waitForResponse(r=>r.url().endsWith('/api/documents')&&r.status()===422,{timeout:25000});
 await page.locator('input[type=file]').setInputFiles({name:'bad.json',mimeType:'application/json',buffer:Buffer.from('{')});
 await rejected;
 await expect(page.getByRole('alert')).toContainText('Document rejected');
});

test('business draft approval records a snapshot and cannot execute externally',async({page})=>{
 await page.locator('nav').getByRole('button',{name:'Business',exact:true}).click();
 await page.getByRole('button',{name:'Compose draft'}).click();
 await page.getByLabel('Title',{exact:true}).fill('Owner review draft');
 await page.getByLabel('Content',{exact:true}).fill('A private draft for review.');
 await page.getByRole('button',{name:'Save draft'}).click();
 // Draft list must refresh without reloading the page.
 await expect(page.locator('.drafts')).toContainText('Owner review draft');
 await page.locator('.drafts summary').filter({hasText:'Owner review draft'}).click();
 page.once('dialog',d=>d.accept());await page.getByRole('button',{name:'Request review'}).click();
 await page.locator('nav').getByRole('button',{name:'Security',exact:true}).click();
 await expect(page.locator('.review')).toContainText('A private draft for review.');
 await page.getByRole('button',{name:'Approve draft',exact:true}).click();
 await expect(page.locator('.review')).toContainText('approved');
 await expect(page.getByRole('button',{name:'Approve draft',exact:true})).toHaveCount(0);
});

test('council runs durable sequential steps and exports a result',async({page})=>{
 await page.locator('nav').getByRole('button',{name:'Model Council',exact:true}).click();
 await page.getByLabel('fixture-a',{exact:true}).check();await page.getByLabel('fixture-b',{exact:true}).check();
 await page.getByLabel('Task question').fill('Compare local data storage options');
 await page.getByRole('button',{name:'Start council'}).click();
 await expect(page.locator('.job-detail .status').first()).toContainText('completed',{timeout:60000});
 await expect(page.locator('.job-detail')).toContainText('fixture-a · independent analysis');
 await expect(page.locator('.job-detail')).toContainText('fixture-b · independent analysis');
 await page.screenshot({path:'test-results/core-council.png',fullPage:true});
});

test('mobile navigation and theme work',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 await page.getByLabel('Open navigation').click();
 await page.locator('nav').getByRole('button',{name:'Settings',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Settings',exact:true})).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
 await page.screenshot({path:'test-results/settings-mobile.png',fullPage:true});
});

test('model recovery and first-run guidance work independently of Computer Mode',async({page})=>{
 await page.evaluate(()=>localStorage.setItem('foxory-model','removed-local-model'));
 await page.reload();
 await expect(page.getByLabel('Select model',{exact:true})).toHaveValue('fixture-a');
 await page.route('**/api/models',route=>route.fulfill({json:{available:true,models:[]}}));
 await page.reload();
 await expect(page.getByText('No local models are installed.',{exact:true})).toBeVisible();
 await expect(page.getByRole('button',{name:'Send message'})).toBeDisabled();
 await page.screenshot({path:'test-results/core-first-run.png',fullPage:true});
 await page.getByRole('button',{name:'Choose a model',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Settings',exact:true})).toBeVisible();
 await expect(page.getByText('Chat, research, documents and safe agents work without Computer Mode.',{exact:true})).toBeVisible();
});


test('account workspace switch isolates history and logout revokes access',async({page})=>{
 await page.getByLabel('Message FOXORY').fill('Private original workspace message');
 await page.getByRole('button',{name:'Send message'}).click();
 await expect(page.locator('.message.assistant')).toContainText('Test fixture response');
 await page.locator('nav').getByRole('button',{name:'Settings',exact:true}).click();
 await page.getByLabel('New workspace name').fill('Browser isolated workspace');
 await page.getByRole('button',{name:'Create workspace',exact:true}).click();
 await expect(page.getByLabel('Current workspace')).toContainText('Browser isolated workspace');
 await expect(page.locator('.history')).not.toContainText('Private original workspace message');
 await page.getByLabel('Lock workspace').click();
 await expect(page.getByRole('button',{name:'Sign in',exact:true})).toBeVisible();
 const denied=await page.request.get('/api/overview');expect(denied.status()).toBe(401);
});

test('document semantic controls and deep research sources/history/exports are connected',async({page})=>{
 test.setTimeout(120000);
 await page.locator('nav').getByRole('button',{name:'Documents',exact:true}).click();
 await page.locator('input[type=file]').setInputFiles({name:'research-evidence.txt',mimeType:'text/plain',buffer:Buffer.from('Revenue was 123 units in June. The source is a fictional test document for interface verification.')});
 const card=page.locator('.record-card').filter({has:page.getByRole('heading',{name:'research-evidence.txt',exact:true})});
 await expect(card).toBeVisible({timeout:20000});
 await card.getByLabel('Local embedding model').selectOption('fixture-a');
 await card.getByRole('button',{name:'Build semantic index'}).click();
 await expect(card.getByRole('status')).toContainText('Indexed 1 chunks');
 await page.locator('nav').getByRole('button',{name:/^Deep Research/}).click();
 await page.getByText('Evidence & resource budgets',{exact:true}).click();
 await page.getByLabel('Research documents').selectOption({label:'research-evidence.txt'});
 await page.getByLabel('Use uploaded documents only').check();
 await page.getByLabel('Task question').fill('What was revenue in June?');
 await page.getByRole('button',{name:'Start research',exact:true}).click();
 await expect(page.locator('.job-detail .status').first()).toContainText('completed',{timeout:60000});
 await expect(page.locator('.job-detail')).toContainText('Extractive evidence report');
 await page.getByRole('button',{name:'Check saved references'}).click();
 await expect(page.locator('.job-detail').getByRole('status')).toContainText('content hashes match');
 await page.locator('.source-card summary').first().click();
 await expect(page.locator('.source-card')).toContainText('Revenue was 123 units');
 await page.screenshot({path:'test-results/core-research.png',fullPage:true});
 const file=page.waitForEvent('download');await page.locator('.job-detail').getByRole('button',{name:'PDF',exact:true}).click();
 expect((await file).suggestedFilename()).toBe('report.pdf');
 await page.reload();
 await page.locator('nav').getByRole('button',{name:/^Deep Research/}).click();
 await page.locator('.job-item').filter({hasText:'What was revenue in June?'}).first().click();
 await expect(page.locator('.job-detail')).toContainText('Extractive evidence report');
});


test('AI Workforce creates agents, delegates real tools, schedules work and manages memory',async({page})=>{
 test.setTimeout(120000);
 await page.getByRole('button',{name:'AI Workforce',exact:false}).first().click();
 await page.getByRole('button',{name:'Templates',exact:true}).click();
 await page.getByRole('button',{name:'Use Data Analysis Agent',exact:true}).click();
 await page.getByLabel('Agent name',{exact:true}).fill('Browser specialist');
 await page.getByRole('button',{name:'Next: permissions',exact:true}).click();
 await page.getByRole('button',{name:'Save agent',exact:true}).click();
 await expect(page.getByRole('button',{name:'Close editor'})).toHaveCount(0);
 await page.getByRole('button',{name:'Agents',exact:true}).click();
 await page.getByRole('button',{name:'Create agent',exact:true}).click();
 await page.getByLabel('Agent name',{exact:true}).fill('Browser coordinator');
 await page.getByRole('button',{name:'Next: permissions',exact:true}).click();
 await page.getByLabel('Browser specialist',{exact:true}).check();
 await page.getByRole('button',{name:'Save agent',exact:true}).click();
 await expect(page.getByRole('button',{name:'Configure Browser coordinator'})).toBeVisible();
 await page.getByRole('button',{name:'Tasks',exact:true}).click();
 await page.getByLabel('Task agent',{exact:true}).selectOption({label:'Browser coordinator'});
 await page.getByLabel('Task objective',{exact:true}).fill('Delegate calculation to the specialist');
 await page.getByRole('button',{name:'Run agent task',exact:true}).click();
 await expect(page.getByRole('status')).toContainText('completed',{timeout:30000});
 await expect(page.getByText('Calculate actual arithmetic → Browser specialist',{exact:false})).toBeVisible();
 await page.screenshot({path:'test-results/core-agents.png',fullPage:true});
 await page.getByRole('button',{name:'Memory',exact:true}).last().click();
 await page.getByLabel('Memory agent',{exact:true}).selectOption({label:'Browser coordinator'});
 await page.getByLabel('Fact title').fill('Preferred review');
 await page.getByLabel('User-approved fact').fill('Always inspect original evidence.');
 await page.getByRole('button',{name:'Approve and save fact'}).click();
 await expect(page.getByRole('heading',{name:'Preferred review'})).toBeVisible();
 await page.getByRole('button',{name:'Edit fact'}).click();
 await page.getByLabel('User-approved fact').fill('Inspect original evidence and dates.');
 await page.getByRole('button',{name:'Update approved fact'}).click();
 await expect(page.getByText('Inspect original evidence and dates.',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Schedules',exact:true}).click();
 await page.getByLabel('Scheduled agent').selectOption({label:'Browser coordinator'});
 await page.getByLabel('Scheduled objective').fill('Tomorrow summary');
 await page.getByLabel('Start time').fill('2030-01-01T10:00');
 await page.getByRole('button',{name:'Save schedule'}).click();
 await expect(page.getByRole('heading',{name:'Tomorrow summary'})).toBeVisible();
 await page.getByRole('button',{name:'Pause schedule'}).click();
 await expect(page.getByRole('button',{name:'Resume schedule'})).toBeVisible();
 await page.getByRole('button',{name:'Resume schedule'}).click();
 await expect(page.getByRole('button',{name:'Pause schedule'})).toBeVisible();
});

test('AI Workforce blocks workspace writes until an immutable approval is consumed',async({page})=>{
 test.setTimeout(90000);
 await page.getByRole('button',{name:'AI Workforce',exact:false}).first().click();
 await page.getByRole('button',{name:'Templates',exact:true}).click();
 await page.getByRole('button',{name:'Use Workflow Agent',exact:true}).click();
 await page.getByRole('button',{name:'Next: permissions',exact:true}).click();
 await page.getByRole('button',{name:'Save agent',exact:true}).click();
 await page.getByRole('button',{name:'Tasks',exact:true}).click();
 await page.getByLabel('Task agent',{exact:true}).selectOption({label:'Workflow Agent'});
 await page.getByLabel('Task objective',{exact:true}).fill('Request approval to create an internal project');
 await page.getByRole('button',{name:'Run agent task',exact:true}).click();
 await expect(page.getByRole('status')).toContainText('awaiting_approval',{timeout:60000});
 await page.getByRole('button',{name:'Approvals',exact:true}).click();
 await expect(page.getByText('Immutable approval context',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'approve action',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Allow project.create · consumed'})).toBeVisible({timeout:60000});
 await page.getByRole('button',{name:'Projects',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Browser agent project'})).toBeVisible();
});

test('Computer Mode runs reviewed Python through actual isolated manager and approvals',async({page})=>{
 test.skip(process.env.FOXORY_E2E_SANDBOX!=='1','Requires explicitly enabled real Linux manager test service');
 test.setTimeout(120000);
 await page.getByRole('button',{name:'Computer',exact:true}).click();
 await expect(page.getByRole('status').first()).toContainText('Python single-process sandbox available');
 await page.getByRole('button',{name:'Create restricted Python agent'}).click();
 await page.getByLabel('Execution agent').selectOption({label:'Restricted Python developer'});
 await page.getByLabel('Computer task objective').fill('Test and package a reviewed addition application');
 await page.getByText('Optional reviewed Python source',{exact:true}).click();
 await page.getByLabel('Source files JSON').fill(JSON.stringify({'app.py':'def add(a,b):return a+b\n','test_app.py':'import unittest\nfrom app import add\nclass AppTest(unittest.TestCase):\n def test_add(self):self.assertEqual(add(2,3),5)\nunittest.main()\n'}));
 await page.getByRole('button',{name:'Plan task',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Approval required'})).toBeVisible();
 await page.getByRole('button',{name:'approve computer action'}).click();
 await expect(page.getByRole('heading',{name:'Step 1 · sandbox.python · completed'})).toBeVisible({timeout:45000});
 await expect(page.getByText(/Exit code 0/)).toBeVisible();
 await expect(page.getByRole('heading',{name:'Approval required'})).toBeVisible();
 await page.getByRole('button',{name:'approve computer action'}).click();
 await expect(page.getByRole('button',{name:'Download project ZIP'})).toBeVisible({timeout:45000});
 const [download]=await Promise.all([page.waitForEvent('download'),page.getByRole('button',{name:'Download project ZIP'}).click()]);
 expect(download.suggestedFilename()).toBe('python-project.zip');
 await expect(page.getByRole('status').last()).toContainText('completed');
});

test('Computer Mode JS packaging and offline browser artifacts through mocked OCI lifecycle',async({page})=>{
 test.skip(process.env.FOXORY_E2E_OCI!=='1','Requires the explicit test-only mocked OCI manager');
 test.setTimeout(180000);
 await page.getByRole('button',{name:'Computer',exact:true}).click();
 await page.getByLabel('Execution profile').selectOption('javascript');
 await expect(page.getByRole('status').first()).toContainText('JavaScript isolated worker available');
 await page.getByRole('button',{name:'Create restricted JavaScript agent',exact:true}).click();
 await page.getByLabel('Execution agent').selectOption({label:'Restricted JavaScript developer'});
 await page.getByLabel('Computer task objective').fill('MOCK OCI: test and package a reviewed dependency-free JavaScript project');
 await page.getByText('Optional reviewed JavaScript source',{exact:true}).click();
 await page.getByLabel('Source files JSON').fill(JSON.stringify({'test_app.js':'if(6*7!==42)throw Error("test failed");'}));
 await page.getByRole('button',{name:'Plan task',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Approval required'})).toBeVisible();
 await page.getByRole('button',{name:'approve computer action'}).click();
 await expect(page.getByRole('heading',{name:'Step 1 · sandbox.javascript · completed'})).toBeVisible();
 await expect(page.getByRole('heading',{name:'Approval required'})).toBeVisible();
 await page.getByRole('button',{name:'approve computer action'}).click();
 const [zip]=await Promise.all([page.waitForEvent('download'),page.getByRole('button',{name:'Download project ZIP'}).click()]);
 expect(zip.suggestedFilename()).toBe('javascript-project.zip');
 await page.getByLabel('Execution profile').selectOption('browser');
 await page.getByRole('button',{name:'Create restricted Offline browser agent',exact:true}).click();
 await page.getByLabel('Execution agent').selectOption({label:'Restricted Offline browser developer'});
 await page.getByLabel('Computer task objective').fill('MOCK OCI: inspect a controlled offline browser fixture');
 if(!await page.getByLabel('Source files JSON').isVisible())await page.getByText('Optional reviewed Offline browser source',{exact:true}).click();
 await page.getByLabel('Source files JSON').fill(JSON.stringify({'index.html':'<!doctype html><html><body><input id="name"><button id="show">Show</button><p id="result"></p><a download href="/report.txt">Download</a></body></html>','report.txt':'Controlled download'}));
 await page.getByLabel('Browser actions JSON').fill(JSON.stringify([{action:'navigate',target:'/'},{action:'type',target:'#name',text:'FOXORY browser fixture'},{action:'click',target:'#show'},{action:'inspect'},{action:'screenshot'},{action:'download',target:'a'}]));
 await page.getByRole('button',{name:'Plan task',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Approval required'})).toBeVisible();
 await page.getByRole('button',{name:'approve computer action'}).click();
 await expect(page.getByRole('heading',{name:'Step 1 · sandbox.browser · completed'})).toBeVisible();
 await expect(page.getByAltText('Validated isolated browser screenshot')).toBeVisible();
 const [png]=await Promise.all([page.waitForEvent('download'),page.getByRole('button',{name:'Download screenshot-1.png',exact:true}).click()]);
 expect(png.suggestedFilename()).toBe('screenshot-1.png');
 await expect(page.getByText(/MOCK OCI boundary: no code or browser executed/)).toBeVisible();
});

test('Computer Mode exposes failures, fresh retry approval, pause and cancellation with mocked OCI',async({page})=>{
 test.skip(process.env.FOXORY_E2E_OCI!=='1','Explicit test-only OCI fixtures required');
 test.setTimeout(180000);
 await page.getByRole('button',{name:'Computer',exact:true}).click();
 await page.getByLabel('Execution profile').selectOption('javascript');
 await page.getByRole('button',{name:'Create restricted JavaScript agent',exact:true}).click();
 await page.getByLabel('Execution agent').selectOption({label:'Restricted JavaScript developer'});
 await page.getByLabel('Computer task objective').fill('MOCK OCI: verify visible failed execution');
 await page.getByText('Optional reviewed JavaScript source',{exact:true}).click();
 await page.getByLabel('Source files JSON').fill(JSON.stringify({'test_app.js':'// FOXORY_FIXTURE_FAIL: explicit test-only result'}));
 await page.getByRole('button',{name:'Plan task',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Approval required'})).toBeVisible();
 await page.getByRole('button',{name:'approve computer action'}).click();
 await expect(page.getByRole('heading',{name:'Step 1 · sandbox.javascript · failed'})).toBeVisible();
 await expect(page.getByRole('button',{name:'Download project ZIP'})).toHaveCount(0);
 await page.getByRole('button',{name:'Review and retry as a new task'}).click();
 await page.getByLabel('Source files JSON').fill(JSON.stringify({'test_app.js':'// FOXORY_FIXTURE_HANG: explicit test-only delayed boundary'}));
 await page.getByRole('button',{name:'Plan task',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Approval required'})).toBeVisible();
 await page.getByRole('button',{name:'approve computer action'}).click();
 await expect(page.getByRole('status').last()).toContainText('running');
 await page.getByRole('button',{name:'pause task',exact:true}).click();
 await expect(page.getByRole('button',{name:'resume task',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'cancel task',exact:true}).click();
 await expect(page.getByRole('status').last()).toContainText('cancelled');
});
