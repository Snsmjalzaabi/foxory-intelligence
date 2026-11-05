import {test,expect,type Page} from '@playwright/test';

async function openTool(page:Page,name:string){
 if(name==='Chat'){if(await page.getByRole('button',{name:'Close chat panel',exact:true}).count())await page.getByRole('button',{name:'Close chat panel',exact:true}).click();return;}
 if(await page.locator('.sidebar.open').count())await page.getByRole('button',{name:'Close conversations',exact:true}).click();
 await page.getByRole('button',{name:'Workspace tools',exact:true}).click();
 const menu=page.getByRole('dialog',{name:'Chat tools',exact:true});
 if(!await menu.getByRole('button',{name,exact:true}).count())await menu.getByRole('button',{name:'Show all tools',exact:true}).click();
 await menu.getByRole('button',{name,exact:true}).click();
}

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
 await expect(page.getByRole('heading',{name:'Welcome to your local AI workspace.'})).toBeVisible({timeout:20000});
});

test('chat streams, persists, regenerates and exports through the real HTTP adapter',async({page})=>{
 await openTool(page,'Settings');
 await page.getByRole('combobox',{name:'Response budget',exact:true}).selectOption('128');
 await openTool(page,'Chat');
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
 await openTool(page,'Documents');
 await page.locator('input[type=file]').setInputFiles({name:'quarter.txt',mimeType:'text/plain',buffer:Buffer.from('Quarter revenue was 100 units.')});
 await expect(page.getByRole('heading',{name:'quarter.txt',exact:true})).toBeVisible({timeout:20000});
 await page.getByLabel('Document question').fill('What was revenue?');
 await page.getByRole('button',{name:'Ask documents'}).click();
 await expect(page.locator('.message.assistant').last()).toContainText('Extractive evidence report');
 await expect(page.locator('.message.assistant').last()).toContainText('Quarter revenue was 100 units');
 await expect(page.locator('.message.assistant').last()).toContainText('quarter.txt');
 await page.screenshot({path:'test-results/core-documents.png',fullPage:true});
 const rejected=page.waitForResponse(r=>r.url().endsWith('/api/documents')&&r.status()===422,{timeout:25000});
 await page.locator('input[type=file]').setInputFiles({name:'bad.json',mimeType:'application/json',buffer:Buffer.from('{')});
 await rejected;
 await expect(page.getByRole('alert')).toContainText('Document rejected');
});

test('business draft approval records a snapshot and cannot execute externally',async({page})=>{
 await openTool(page,'Business');
 await page.getByRole('button',{name:'Drafts',exact:true}).click();
 await page.getByRole('button',{name:'Compose draft'}).click();
 await page.getByLabel('Title',{exact:true}).fill('Owner review draft');
 await page.getByLabel('Content',{exact:true}).fill('A private draft for review.');
 await page.getByRole('button',{name:'Save draft'}).click();
 // Draft list must refresh without reloading the page.
 await expect(page.locator('.drafts')).toContainText('Owner review draft');
 await page.locator('.drafts summary').filter({hasText:'Owner review draft'}).click();
 page.once('dialog',d=>d.accept());await page.getByRole('button',{name:'Request review'}).click();
 await openTool(page,'Security');
 await expect(page.locator('.review')).toContainText('A private draft for review.');
 await page.getByRole('button',{name:'Approve draft',exact:true}).click();
 await expect(page.locator('.review')).toContainText('approved');
 await expect(page.getByRole('button',{name:'Approve draft',exact:true})).toHaveCount(0);
});

test('council runs durable sequential steps and exports a result',async({page})=>{
 await openTool(page,'Model Council');
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
 await page.getByLabel('Open conversations').click();
 await openTool(page,'Settings');
 await expect(page.getByRole('heading',{name:'Settings',exact:true})).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
 await page.screenshot({path:'test-results/settings-mobile.png',fullPage:true});
});

test('model recovery and first-run guidance work independently of Computer Mode',async({page})=>{
 await page.evaluate(()=>localStorage.setItem('foxory-model','removed-local-model'));
 await page.reload();
 await expect(page.getByLabel('Select model',{exact:true})).toHaveValue('auto');
 await page.route('**/api/models',route=>route.fulfill({json:{available:true,models:[]}}));
 await page.reload();
 await expect(page.getByText('No local models are installed.',{exact:true})).toBeVisible();
 await expect(page.getByRole('button',{name:'Send message'})).toBeDisabled();
 await page.screenshot({path:'test-results/core-first-run.png',fullPage:true});
 await page.getByRole('button',{name:'Choose a model',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Settings',exact:true})).toBeVisible();
 await expect(page.getByText('Chat, research, documents and safe agents work without Computer Mode.',{exact:true})).toBeVisible();
});

test('reported model capabilities separate chat, council and document embeddings',async({page})=>{
 await page.route('**/api/models',route=>route.fulfill({json:{available:true,models:[
  {name:'embed-fixture',size:100,capabilities:['embedding'],capability_status:'reported',completion_supported:false,embedding_supported:true},
  {name:'fixture-a',size:100,capabilities:['completion'],capability_status:'reported',completion_supported:true,embedding_supported:false},
  {name:'legacy-model',size:100,capability_status:'unknown',completion_supported:null,embedding_supported:null}
 ]}}));
 await page.reload();
 const choice=page.getByLabel('Select model',{exact:true});
 await expect(choice).toHaveValue('auto');
 await expect(choice.locator('option')).not.toContainText(['embed-fixture']);
 await openTool(page,'Model Council');
 await expect(page.getByRole('checkbox',{name:'embed-fixture',exact:true})).toHaveCount(0);
 await expect(page.getByRole('checkbox',{name:'legacy-model',exact:true})).toBeVisible();
 await openTool(page,'Documents');
 await page.locator('input[type=file]').setInputFiles({name:'capabilities.txt',mimeType:'text/plain',buffer:Buffer.from('Fictional capability test evidence.')});
 const model=page.getByLabel('Local embedding model').last();
 await expect(model.locator('option')).toContainText(['embed-fixture']);
 expect(await model.locator('option').allTextContents()).not.toContain('fixture-a');
});


test('account workspace switch isolates history and logout revokes access',async({page})=>{
 await page.getByLabel('Message FOXORY').fill('Private original workspace message');
 await page.getByRole('button',{name:'Send message'}).click();
 await expect(page.locator('.message.assistant')).toContainText('Test fixture response');
 await openTool(page,'Settings');
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
 await openTool(page,'Documents');
 await page.locator('input[type=file]').setInputFiles({name:'research-evidence.txt',mimeType:'text/plain',buffer:Buffer.from('Revenue was 123 units in June. The source is a fictional test document for interface verification.')});
 const card=page.locator('.record-card').filter({has:page.getByRole('heading',{name:'research-evidence.txt',exact:true})});
 await expect(card).toBeVisible({timeout:20000});
 await card.getByLabel('Local embedding model').selectOption('fixture-a');
 await card.getByRole('button',{name:'Build semantic index'}).click();
 await expect(card.getByRole('status')).toContainText('Indexed 1 chunks');
 await openTool(page,'Deep Research');
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
 await openTool(page,'Deep Research');
 await page.locator('.job-item').filter({hasText:'What was revenue in June?'}).first().click();
 await expect(page.locator('.job-detail')).toContainText('Extractive evidence report');
});


test('AI Workforce creates agents, delegates real tools, schedules work and manages memory',async({page})=>{
 test.setTimeout(120000);
 await openTool(page,'AI Workforce');
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
 await openTool(page,'AI Workforce');
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
 await openTool(page,'Projects');
 await expect(page.getByRole('heading',{name:'Browser agent project'})).toBeVisible();
});

test('Computer Mode runs reviewed Python through actual isolated manager and approvals',async({page})=>{
 test.skip(process.env.FOXORY_E2E_SANDBOX!=='1','Requires explicitly enabled real Linux manager test service');
 test.setTimeout(120000);
 await openTool(page,'Computer');
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
 await openTool(page,'Computer');
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
 await openTool(page,'Computer');
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

 test('FOXORY personal starters prepare prompts without sending and route documents',async({page})=>{
 await page.getByRole('button',{name:/Plan my day/}).click();
 await expect(page.getByLabel('Message FOXORY')).toHaveValue(/saved priorities/);
 await expect(page.locator('.message')).toHaveCount(0);
 await page.getByRole('button',{name:/Build on your computer/}).click();
 await expect(page.getByLabel('Message FOXORY')).toHaveValue(/your Ubuntu computer/);
 await page.getByRole('button',{name:/Draft for FOXORY/}).click();
 await expect(page.getByLabel('Message FOXORY')).toHaveValue(/business message/);
 await page.getByRole('button',{name:/Review my documents/}).click();
 await expect(page.getByRole('heading',{name:'Ask your document library'})).toBeVisible();
 });


test('business pipeline persists actions, stages and prompts without submitting AI work',async({page})=>{
 await openTool(page,'Business');
 await page.getByRole('button',{name:'New opportunity',exact:true}).click();
 await page.getByLabel('Opportunity name',{exact:true}).fill('Author formatting service');
 await page.getByLabel('Who is it for?',{exact:true}).fill('Independent authors');
 await page.getByLabel('Your offer',{exact:true}).fill('Format one manuscript for review');
 await page.getByLabel('Estimated deal value',{exact:true}).fill('250');
 await page.getByLabel('Next action',{exact:true}).fill('Prepare a sample');
 await page.getByLabel('New action',{exact:true}).fill('Create sample PDF');
 await page.getByRole('button',{name:'Add action',exact:true}).click();
 await page.getByRole('button',{name:'Save opportunity',exact:true}).click();
 const card=page.locator('.opportunity-card').filter({hasText:'Author formatting service'});
 await expect(card).toBeVisible();
 await card.getByRole('combobox').selectOption('validating');
 const savedAction=page.waitForResponse(r=>r.url().includes('/business/opportunities/')&&r.request().method()==='PUT'&&r.request().postDataJSON().actions?.[0]?.done===true);
 await card.getByRole('checkbox',{name:'Create sample PDF'}).check();
 await savedAction;
 await page.reload();
 await openTool(page,'Business');
 await expect(card.getByRole('combobox')).toHaveValue('validating');
 await expect(card.getByRole('checkbox',{name:'Create sample PDF'})).toBeChecked();
 await page.screenshot({path:'test-results/business-pipeline.png',fullPage:true});
 await page.setViewportSize({width:390,height:844});
 await page.screenshot({path:'test-results/business-mobile.png',fullPage:true});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
 await card.getByRole('button',{name:'Draft offer',exact:true}).click();
 await expect(page.getByLabel('Message FOXORY')).toHaveValue(/Author formatting service/);
 await expect(page.locator('.message')).toHaveCount(0);
});

test('guided business team creates only missing roles and settings persist',async({page})=>{
 await openTool(page,'AI Workforce');
 await page.getByRole('button',{name:'Build my team',exact:true}).click();
 await page.getByRole('combobox',{name:'Team model',exact:true}).selectOption('fixture-a');
 await page.getByRole('button',{name:'Create 5 selected agents',exact:true}).click();
 await expect(page.getByRole('status')).toContainText('5 agents created');
 await expect(page.getByRole('heading',{name:'FOXORY Business Planner',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Build my team',exact:true}).click();
 await page.getByRole('button',{name:'Create 5 selected agents',exact:true}).click();
 await expect(page.getByRole('status')).toContainText('0 agents created · 5 existing agents preserved');
 await page.screenshot({path:'test-results/business-team.png',fullPage:true});
 await openTool(page,'Settings');
 await page.getByRole('combobox',{name:'Keep model ready',exact:true}).selectOption('30');
 await page.getByRole('button',{name:'Save inference preferences',exact:true}).click();
 await expect(page.locator('.local-runtime').getByRole('status')).toContainText('Saved.');
 await page.reload();
 await openTool(page,'Settings');
 await expect(page.getByRole('combobox',{name:'Keep model ready',exact:true})).toHaveValue('30');
});

test('business opportunity connects to a durable local agent task',async({page})=>{
 test.setTimeout(45000);
 await openTool(page,'AI Workforce');
 await page.getByRole('button',{name:'Templates',exact:true}).click();
 await page.getByRole('button',{name:'Use Data Analysis Agent',exact:true}).click();
 await page.getByLabel('Agent name',{exact:true}).fill('Opportunity analysis specialist');
 await page.getByRole('button',{name:'Next: permissions',exact:true}).click();
 await page.getByRole('button',{name:'Save agent',exact:true}).click();
 await expect(page.getByRole('button',{name:'Close editor'})).toHaveCount(0);
 await openTool(page,'Business');
 await page.getByRole('button',{name:'New opportunity',exact:true}).click();
 await page.getByLabel('Opportunity name',{exact:true}).fill('Connected service experiment');
 await page.getByLabel('Your offer',{exact:true}).fill('A scoped deliverable');
 await page.getByRole('button',{name:'Save opportunity',exact:true}).click();
 const card=page.locator('.opportunity-card').filter({hasText:'Connected service experiment'});
 await card.getByRole('button',{name:'Assign to agent',exact:true}).click();
 await page.getByLabel('Business task agent',{exact:true}).selectOption({label:'Opportunity analysis specialist'});
 await page.getByLabel('Agent objective',{exact:true}).fill('Calculate a bounded check for this offer');
 await page.getByRole('button',{name:'Run business task',exact:true}).click();
 await expect(page.getByRole('status')).toContainText('completed',{timeout:30000});
 await expect(page.locator('.agent-result')).not.toBeEmpty();
 await openTool(page,'Business');
 await card.getByRole('combobox').selectOption('validating');
 await page.reload();
 await openTool(page,'Business');
 await card.getByRole('button',{name:'Open latest task',exact:true}).click();
 await expect(page.getByRole('status')).toContainText('completed');
});

test('personal chat preferences survive reload and stay separate between workspaces',async({page})=>{
 test.setTimeout(45000);
 await openTool(page,'Settings');
 await page.getByRole('combobox',{name:'Response budget',exact:true}).selectOption('512');
 await page.getByLabel('System instructions',{exact:true}).fill('Personal browser preference example.');
 await page.reload();
 await openTool(page,'Settings');
 await expect(page.getByRole('combobox',{name:'Response budget',exact:true})).toHaveValue('512');
 await expect(page.getByLabel('System instructions',{exact:true})).toHaveValue('Personal browser preference example.');
 await page.getByLabel('New workspace name',{exact:true}).fill('Preference isolation workspace');
 await page.getByRole('button',{name:'Create workspace',exact:true}).click();
 await expect(page.getByRole('combobox',{name:'Response budget',exact:true})).toHaveValue('2048');
 await expect(page.getByLabel('System instructions',{exact:true})).not.toHaveValue('Personal browser preference example.');
});

test('appearance colors, navigation order and sidebar placement persist with safe discard',async({page})=>{
 await page.getByRole('button',{name:'Customize appearance',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Appearance',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Midnight Ocean',exact:true}).click();
 await page.getByLabel('Accent color hex',{exact:true}).fill('#ffcc66');
 await page.getByRole('combobox',{name:'Sidebar placement',exact:true}).selectOption('right');
 await page.getByRole('combobox',{name:'Page density',exact:true}).selectOption('compact');
 await page.getByRole('button',{name:'Move Business up',exact:true}).click();
 await page.getByRole('checkbox',{name:'Search',exact:true}).uncheck();
 await page.getByRole('button',{name:'Save appearance',exact:true}).click();
 await page.reload();
 await expect(page.locator('html')).toHaveAttribute('data-sidebar-position','right');
 expect(await page.evaluate(()=>document.documentElement.style.getPropertyValue('--accent'))).toBe('#ffcc66');
 await page.getByRole('button',{name:'Workspace tools',exact:true}).click();
 await expect(page.locator('.chat-tool-options').getByRole('button',{name:'Search',exact:true})).toHaveCount(0);
 const names=await page.locator('.chat-tool-options button').allTextContents();
 expect(names.findIndex(n=>n==='Business')).toBeLessThan(names.findIndex(n=>n.startsWith('Computer')));
 await page.getByRole('button',{name:'Close tools menu',exact:true}).click();
 await page.getByRole('button',{name:'Customize appearance',exact:true}).click();
 await page.getByRole('button',{name:'Warm Paper',exact:true}).click();
 await page.getByRole('button',{name:'Discard preview',exact:true}).click();
 expect(await page.evaluate(()=>document.documentElement.style.getPropertyValue('--bg'))).toBe('#0b1220');
 await page.screenshot({path:'test-results/appearance-editor.png',fullPage:true});
});

test('design import validates values, rearranges dashboard and keeps mobile navigation usable',async({page})=>{
 await page.getByRole('button',{name:'Customize appearance',exact:true}).click();
 await page.locator('.appearance-editor input[type=file]').setInputFiles({name:'design.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify({version:1,appearance:{brand:'FOXORY Studio',palette:'violet',sidebar:'top',sidebarWidth:99999,contentWidth:1200,columns:2,hidden:['Appearance','Settings','Search'],navigation:['Business','Appearance','Settings'],dashboard:['Tasks','Inventory','Metrics','Services'],colors:{accent:'url(javascript:alert(1))'}}}))});
 await page.getByRole('button',{name:'Save appearance',exact:true}).click();
 await expect(page.locator('html')).toHaveAttribute('data-sidebar-position','top');
 expect(await page.evaluate(()=>document.documentElement.style.getPropertyValue('--sidebar-width'))).toBe('320px');
 await expect(page.locator('.sidebar nav')).toHaveCount(0);
 await openTool(page,'Command Center');
 const first=await page.locator('.command-tasks').boundingBox(),last=await page.locator('.command-services').boundingBox();
 expect(first!.y).toBeLessThan(last!.y);
 await expect(page.locator('.command-layout > :first-child')).toHaveClass('command-tasks');
 await page.setViewportSize({width:390,height:844});
 await page.getByRole('button',{name:'Open conversations',exact:true}).click();
 await openTool(page,'Appearance');
 await expect(page.getByRole('heading',{name:'Appearance',exact:true})).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
 await page.screenshot({path:'test-results/appearance-mobile.png',fullPage:true});
 const exported=page.waitForEvent('download');
 await page.getByRole('button',{name:'Export design',exact:true}).click();
 expect((await exported).suggestedFilename()).toBe('foxory-appearance.json');
 await page.getByRole('button',{name:'Reset design',exact:true}).click();
 await page.getByRole('button',{name:'Save appearance',exact:true}).click();
 await expect(page.locator('html')).toHaveAttribute('data-sidebar-position','left');
});

test('appearance navigation supports drag placement and a reversible preview',async({page})=>{
 await page.getByRole('button',{name:'Customize appearance',exact:true}).click();
 await page.getByLabel('Brand name',{exact:true}).fill('');
 await page.getByLabel('Brand name',{exact:true}).pressSequentially('FOXORY Studio');
 await expect(page.getByLabel('Brand name',{exact:true})).toHaveValue('FOXORY Studio');
 const source=page.getByRole('button',{name:'Move Business up',exact:true}).locator('..');
 const target=page.getByRole('button',{name:'Move Chat up',exact:true}).locator('..');
 await source.locator('.drag-handle').dragTo(target.locator('.drag-handle')); 
 await expect(page.locator('.reorder-list').first().locator(':scope > div').first()).toContainText('Business');
 await page.getByRole('button',{name:'Workspace tools',exact:true}).click();await expect(page.locator('.chat-tool-options button').first()).toHaveText('Business');await page.getByRole('button',{name:'Close tools menu',exact:true}).click();
 await page.getByRole('button',{name:'Discard preview',exact:true}).click();
 await expect(page.locator('.sidebar nav')).toHaveCount(0);
});


test('repository snapshots import real file bytes and pass selected evidence into Council',async({page})=>{
 await openTool(page,'Repositories');
 await page.getByLabel('Public GitHub repository',{exact:true}).fill('git@github.com:fixture-owner/fixture-repo.git');
 await page.getByRole('button',{name:'Preview repository',exact:true}).click();
 await expect(page.getByText('README.md',{exact:true})).toBeVisible();
 await expect(page.getByText('.env',{exact:true})).toHaveCount(0);
 await page.getByRole('button',{name:'Import 2 selected files',exact:true}).click();
 await expect(page.getByRole('status')).toContainText('Imported 2 source files');
 await page.getByText('Imported files and integrity',{exact:true}).click();
 await page.getByRole('button',{name:'Preview source',exact:true}).first().click();
 await expect(page.getByRole('dialog',{name:'Imported source preview'})).toContainText('Fixture project');
 await page.getByRole('button',{name:'Close source preview',exact:true}).click();
 await page.getByRole('button',{name:'Review with Council',exact:true}).click();
 await expect(page.getByLabel('Task question',{exact:true})).toHaveValue(/provided source excerpts/);
 await page.getByText('Evidence & resource budgets',{exact:true}).click();
 await expect(page.getByRole('listbox',{name:'Research documents',exact:true})).toHaveValues([/./,/./]);
 await page.getByLabel('fixture-a',{exact:true}).check();await page.getByLabel('fixture-b',{exact:true}).check();
 await page.getByRole('button',{name:'Start council',exact:true}).click();
 await expect(page.locator('.job-detail .status').first()).toContainText('completed',{timeout:30000});
 await expect(page.locator('.job-detail')).not.toContainText('No external or document sources were provided');
});

test('workspace context can be previewed, disabled and inspected on replies',async({page})=>{
 await openTool(page,'Memory');
 await page.getByRole('button',{name:'Create memory',exact:true}).click();
 await page.getByLabel('Title',{exact:true}).fill('Context release marker');
 await page.getByLabel('Content',{exact:true}).fill('ContextMarker project needs a final book revision.');
 await page.getByRole('button',{name:'Save memory',exact:true}).click();
 await openTool(page,'Settings');
 await page.getByLabel('Context preview question').fill('ContextMarker');
 await page.getByRole('button',{name:'Preview available context',exact:true}).click();
 await page.getByText(/Context used ·/).click();
 await expect(page.locator('.context-details')).toContainText('final book revision');
 await page.getByLabel('Use saved workspace context').uncheck();
 await page.reload();
 await openTool(page,'Settings');
 await expect(page.getByLabel('Use saved workspace context')).not.toBeChecked();
 await page.getByLabel('Use saved workspace context').check();
 await openTool(page,'Chat');
 await page.getByLabel('Message FOXORY').fill('What remains for ContextMarker?');
 await page.getByRole('button',{name:'Send message'}).click();
 await expect(page.locator('.message.assistant .context-details summary')).toContainText('saved excerpts');
 await page.locator('.message.assistant .context-details summary').click();
 await expect(page.locator('.message.assistant .context-details')).toContainText('final book revision');
});

test('V2 writing space saves manuscript revisions, approved facts and isolated project chat',async({page})=>{
 await openTool(page,'Projects');
 await page.getByRole('button',{name:'New project space',exact:true}).click();
 await page.getByLabel('Project title',{exact:true}).fill('V2 writing fixture');
 await page.getByRole('combobox',{name:'Project type',exact:true}).selectOption('writing');
 await page.getByLabel('brief',{exact:true}).fill('Test-only writing project. Finish the final revision.');
 await page.getByRole('button',{name:'Save project',exact:true}).click();
 await expect(page.getByRole('heading',{name:'V2 writing fixture',exact:true})).toBeVisible();
 await expect(page.getByRole('combobox',{name:'Project knowledge space',exact:true})).not.toHaveValue('');
 const id=await page.getByRole('combobox',{name:'Project knowledge space',exact:true}).inputValue();
 await page.getByRole('button',{name:'Writing',exact:true}).click();
 await page.getByRole('button',{name:'Add chapter',exact:true}).click();
 await page.getByLabel('Item title',{exact:true}).fill('Chapter One fixture');
 await page.getByRole('textbox',{name:'Item content',exact:true}).fill('Asha enters Redhaven. Her green eyes catch the light.');
 await page.getByRole('button',{name:'Save item',exact:true}).click();
 let card=page.locator('article.panel').filter({has:page.getByRole('heading',{name:'Chapter One fixture',exact:true})});
 await card.getByRole('button',{name:'Edit / revisions',exact:true}).click();
 await page.getByRole('textbox',{name:'Item content',exact:true}).fill('Asha enters Redhaven. Her blue eyes catch the light.');
 await page.getByRole('button',{name:'Save item',exact:true}).click();
 await card.getByRole('button',{name:'Edit / revisions',exact:true}).click();
 await page.getByText('Saved revision history (1)',{exact:true}).click();
 await expect(page.locator('.modal')).toContainText('Her green eyes');
 await page.getByRole('button',{name:'Close',exact:true}).click();
 await page.getByRole('button',{name:'Knowledge',exact:true}).click();
 await page.getByRole('button',{name:'Add fact',exact:true}).click();
 await page.getByLabel('Item title',{exact:true}).fill('Approved Asha canon');
 await page.getByRole('textbox',{name:'Item content',exact:true}).fill('Asha has blue eyes.');
 await page.getByLabel('Fact key',{exact:true}).fill('asha.eyes');
 await page.getByLabel('Source / reason',{exact:true}).fill('Test fixture owner canon');
 await page.getByRole('combobox',{name:'Review status',exact:true}).selectOption('approved');
 await page.getByRole('button',{name:'Save item',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Approved Asha canon',exact:true})).toBeVisible();
 const [dl]=await Promise.all([page.waitForEvent('download'),page.getByRole('button',{name:'Export ZIP',exact:true}).click()]);
 expect(dl.suggestedFilename()).toBe('foxory-project.zip');
 await page.getByRole('button',{name:'Dashboard',exact:true}).click();
 await page.getByText('Customize project dashboard',{exact:true}).click();
 await page.getByRole('button',{name:'Writing layout',exact:true}).click();
 await page.getByRole('button',{name:'Move Knowledge widget up',exact:true}).click();
 await page.getByRole('combobox',{name:'Manuscript widget width',exact:true}).selectOption('2');
 const briefWidget=page.locator('.dashboard-widget').filter({has:page.getByRole('heading',{name:'V2 writing fixture',exact:true})});
 const actionWidget=page.locator('.dashboard-widget').filter({has:page.getByRole('heading',{name:'Next actions',exact:true})});
 await briefWidget.dragTo(actionWidget);
 await page.getByRole('button',{name:'Save project layout',exact:true}).click();
 await expect(page.getByText('Project layout saved.',{exact:true})).toBeVisible();
 await page.screenshot({path:'test-results/v2-project-desktop.png',fullPage:true});
 const saved=await page.request.get('/api/spaces/'+id);const savedLayout=(await saved.json()).space.data.layout;expect(savedLayout.widgets[0]).toBe('Knowledge');expect(savedLayout.widgets[2]).toBe('Brief');
 await page.setViewportSize({width:390,height:844});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
 await page.screenshot({path:'test-results/v2-project-mobile.png',fullPage:true});
 await page.setViewportSize({width:1280,height:720});
 await page.getByRole('button',{name:'New project chat',exact:true}).click();
 await page.getByLabel('Message FOXORY').fill('What do we know about Asha eyes?');
 await page.getByRole('button',{name:'Send message',exact:true}).click();
 await expect(page.locator('.message.assistant .context-details summary')).toBeVisible();
 await page.locator('.message.assistant .context-details summary').click();
 await expect(page.locator('.message.assistant .context-details')).toContainText('Selected project only');
 await expect(page.locator('.message.assistant .context-details')).toContainText('blue eyes');
});

test('V2 business launch requires evidence and a reviewed deliverable',async({page})=>{
 await openTool(page,'Projects');
 await page.getByRole('button',{name:'New project space',exact:true}).click();
 await page.getByLabel('Project title',{exact:true}).fill('V2 business fixture');
 await page.getByRole('combobox',{name:'Project type',exact:true}).selectOption('business');
 await page.getByLabel('evidence',{exact:true}).fill('Disposable test interview notes, not a real customer claim.');
 await page.getByLabel('Budget',{exact:true}).fill('100');
 await page.getByRole('button',{name:'Save project',exact:true}).click();
 await expect(page.getByRole('heading',{name:'V2 business fixture',exact:true})).toBeVisible();
 await page.locator('.project-spaces .hub-toolbar').getByRole('button',{name:'Business',exact:true}).click();
 await page.getByRole('button',{name:'Draft offer / prototype brief',exact:true}).click();
 await page.getByLabel('Item title',{exact:true}).fill('Reviewed fixture offer');
 await page.getByRole('textbox',{name:'Item content',exact:true}).fill('Test-only draft concept. Price and delivery are unset.');
 await page.getByRole('combobox',{name:'Review status',exact:true}).selectOption('approved');
 await page.getByLabel('Check supplied evidence',{exact:true}).check();
 await page.getByLabel('Remove unsupported claims',{exact:true}).check();
 await page.getByLabel('Verify usable output',{exact:true}).check();
 await page.getByRole('button',{name:'Save item',exact:true}).click();
 const response=page.waitForResponse(r=>r.url().includes('/api/spaces/')&&r.request().method()==='PUT');
 await page.getByRole('button',{name:'launch',exact:true}).click();
 expect((await response).status()).toBe(200);
 await expect(page.getByRole('button',{name:'launch',exact:true})).toHaveClass(/primary/);
});

test('V2 recovery center shows installed version and disconnected controls safely',async({page})=>{
 await openTool(page,'Recovery');
 await expect(page.getByRole('heading',{name:'Local update and recovery center',exact:true})).toBeVisible();
 await expect(page.getByRole('button',{name:'Create private backup',exact:true})).toBeDisabled();
 await expect(page.getByText(/local controller: not_connected/)).toBeVisible();
});

test('V3 one command runs a tested project routine and saves a draft',async({page})=>{
 // Use the normal UI to create the project so CSRF and workspace selection stay real.
 await openTool(page,'Projects');
 await page.getByRole('button',{name:'New project space',exact:true}).click();
 await page.getByRole('textbox',{name:'Project title',exact:true}).fill('V3 automation fixture');
 await page.getByRole('combobox',{name:'Project type',exact:true}).selectOption('business');
 await page.getByRole('button',{name:'Save project',exact:true}).click();
 await expect(page.getByRole('heading',{name:'V3 automation fixture',exact:true})).toBeVisible();
 await openTool(page,'Automation');
 await page.getByRole('button',{name:'Policy',exact:true}).click();
 await page.getByRole('combobox',{name:'Automation model',exact:true}).selectOption('fixture-a');
 await page.getByLabel('V3 automation fixture',{exact:true}).check();
 await page.getByRole('spinbutton',{name:'Projects per mission',exact:true}).fill('1');
 await page.getByLabel('Create up to one new skill proposal per day',{exact:true}).uncheck();
 await page.getByRole('button',{name:'Save automation policy',exact:true}).click();
 await expect(page.getByText('Automation policy saved.',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Missions',exact:true}).click();
 await page.getByRole('button',{name:'Run once',exact:true}).click();
 await expect(page.locator('.mission-card > p').first()).toContainText('completed',{timeout:90000});
 await page.getByRole('button',{name:'Pause project automation',exact:true}).click();
 await expect(page.getByText(/Budget used today:.*Paused/)).toBeVisible();
 await openTool(page,'Projects');
 await page.getByRole('combobox',{name:'Project knowledge space',exact:true}).selectOption({label:'V3 automation fixture · business'});
 await page.locator('.project-spaces .hub-toolbar').getByRole('button',{name:'Deliverables',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Automation draft: V3 automation fixture',exact:true})).toBeVisible();
});

test('V3 generated skill requires a completed test before owner activation and revocation',async({page})=>{
 await openTool(page,'Automation');
 await page.getByRole('button',{name:'Skills',exact:true}).click();
 await page.getByRole('textbox',{name:'New skill goal',exact:true}).fill('Create a concise readonly project checklist skill.');
 await page.getByRole('button',{name:'Draft skill with Ollama',exact:true}).click();
 const card=page.locator('article.panel').filter({has:page.getByRole('heading',{name:'Fixture learned skill',exact:true})});
 await expect(card).toBeVisible();
 await expect(card.getByRole('button',{name:'Activate tested revision',exact:true})).toBeDisabled();
 await card.getByRole('button',{name:'Test skill',exact:true}).click();
 await expect(page.locator('.job-grid article').first()).toContainText('completed',{timeout:90000});
 await openTool(page,'Automation');
 await page.getByRole('button',{name:'Skills',exact:true}).click();
 await card.getByRole('button',{name:'Activate tested revision',exact:true}).click();
 await expect(card.locator('p').first()).toContainText('active');
 await card.getByRole('button',{name:'Revoke skill',exact:true}).click();
 await expect(card.locator('p').first()).toContainText('revoked');
});

test('V4 project overview plans future missions, inspects context and exports a snapshot',async({page})=>{
 await openTool(page,'Projects');
 await page.getByRole('button',{name:'New project space',exact:true}).click();
 await page.getByRole('textbox',{name:'Project title',exact:true}).fill('V4 project planning fixture');
 await page.getByRole('combobox',{name:'Project type',exact:true}).selectOption('writing');
 await page.getByRole('button',{name:'Save project',exact:true}).click();
 await expect(page.getByRole('heading',{name:'V4 project planning fixture',exact:true})).toBeVisible();
 await openTool(page,'Automation');
 await expect(page.getByRole('heading',{name:'All-project overview',exact:true})).toBeVisible();
 const card=page.locator('.operations .artifact-grid > article').filter({has:page.getByRole('heading',{name:'V4 project planning fixture',exact:true})});
 await expect(card).toContainText('No manuscript chapters saved');
 await card.getByRole('button',{name:'Plan this project',exact:true}).click();
 await page.getByLabel('Include in future automation missions',{exact:true}).uncheck();
 await page.getByRole('spinbutton',{name:'Project priority',exact:true}).fill('5');
 await page.getByLabel('Owner direction for the next draft',{exact:true}).fill('Use actual canon; prepare an intake checklist.');
 await page.getByRole('button',{name:'Save project plan',exact:true}).click();
 await expect(card).toContainText('Held from future runs');
 await card.getByRole('button',{name:'Plan this project',exact:true}).click();
 await expect(page.getByLabel('Owner direction for the next draft',{exact:true})).toHaveValue('Use actual canon; prepare an intake checklist.');
 await page.getByRole('button',{name:'Close plan',exact:true}).click();
 await card.getByRole('button',{name:'Inspect saved context',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Saved context · V4 project planning fixture',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Close context',exact:true}).click();
 const downloaded=page.waitForEvent('download');await page.getByRole('button',{name:'Download planning snapshot',exact:true}).click();
 expect((await downloaded).suggestedFilename()).toBe('FOXORY-project-overview.json');
 await page.screenshot({path:'test-results/v4-project-overview.png',fullPage:true});
});

test('V4.1 performance monitor benchmarks locally and preserves automation policy on model choice',async({page})=>{
 await openTool(page,'Automation');
 await page.getByRole('button',{name:'Performance',exact:true}).click();
 await expect(page.getByRole('heading',{name:'your computer performance',exact:true})).toBeVisible();
 await expect(page.getByRole('heading',{name:'Task timing and recovery',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Benchmark fixture-a',exact:true}).click();
 await expect(page.getByText(/fixture-a: .*s elapsed;/)).toBeVisible({timeout:60000});
 await expect(page.getByText(/Latest benchmark:/).first()).toBeVisible();
 await page.getByRole('button',{name:'Use fixture-b for automation',exact:true}).click();
 await expect(page.getByText(/Automation model changed to fixture-b/)).toBeVisible();
 await page.getByRole('button',{name:'Policy',exact:true}).click();
 await expect(page.getByRole('combobox',{name:'Automation model',exact:true})).toHaveValue('fixture-b');
 await page.getByRole('button',{name:'Performance',exact:true}).click();
 await page.screenshot({path:'test-results/v4.1-performance.png',fullPage:true});
});

test('V5 Evolution Lab generates an exact code diff without approving installation',async({page})=>{
 await openTool(page,'Automation');
 await page.getByRole('button',{name:'Evolution',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Evolution Lab',exact:true})).toBeVisible();
 await page.getByRole('combobox',{name:'Evolution model',exact:true}).selectOption('fixture-a');
 await page.getByLabel('Improvement goal',{exact:true}).fill('Clarify the performance overview title without changing any behavior.');
 await page.getByRole('button',{name:'Save evolution policy',exact:true}).click();
 await expect(page.getByText(/Evolution policy saved/)).toBeVisible();
 await page.getByRole('button',{name:'Run self-review now',exact:true}).click();
 const card=page.locator('.mission-card').filter({has:page.getByRole('heading',{name:'Fixture performance clarity improvement',exact:true})});
 await expect(card).toBeVisible({timeout:60000});
 await card.getByText('Inspect exact code diff',{exact:true}).click();
 await expect(card.locator('pre')).toContainText('your computer performance overview');
 await expect(page.getByRole('button',{name:'Approve and install this candidate',exact:true})).toHaveCount(0);
 const downloaded=page.waitForEvent('download');await card.getByRole('button',{name:'Download code diff',exact:true}).click();expect((await downloaded).suggestedFilename()).toBe('FOXORY-evolution.patch');
 await card.getByLabel(/Rejection feedback/).fill('Prefer an actual usability improvement over a title change.');
 await card.getByRole('button',{name:'Reject and teach from feedback',exact:true}).click();
 await expect(card).toContainText('rejected');
 await page.screenshot({path:'test-results/v5-evolution-lab.png',fullPage:true});
});

test('V6 chat teaches preferences and opens skills without losing conversation or draft',async({page})=>{
 await expect(page.locator('.sidebar nav')).toHaveCount(0);
 await page.getByLabel('Message FOXORY').fill('from now on use concise checklists for planning');
 await page.getByRole('button',{name:'Send message',exact:true}).click();
 await expect(page.locator('.message.assistant').last()).toContainText('Saved your preference');
 await expect(page.getByRole('heading',{name:'Learned from our conversations',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Close chat panel',exact:true}).click();
 await page.getByLabel('Message FOXORY').fill('UNSENT_DRAFT_MARKER');
 await openTool(page,'Skills');
 await expect(page.getByRole('heading',{name:'Skill library',exact:true})).toBeVisible();
 await expect(page.getByLabel('Message FOXORY')).toHaveValue('UNSENT_DRAFT_MARKER');
 await expect(page.locator('.message.assistant').last()).toContainText('Saved your preference');
 await page.getByRole('button',{name:'Close chat panel',exact:true}).click();
 await page.getByLabel('Message FOXORY').fill('Plan the next step');
 await page.getByRole('button',{name:'Send message',exact:true}).click();
 await expect(page.locator('.message.assistant').last()).toContainText('Test fixture response');
 await expect(page.getByText(/Used 1 saved conversational learning items/)).toBeVisible();
 await page.reload();
 await page.locator('.history-row').filter({hasText:'from now on use concise'}).first().locator('button').first().click();
 await expect(page.locator('.message.assistant').first()).toContainText('Saved your preference');
 await expect(page.locator('.message.assistant').last()).toContainText('Test fixture response');
 await expect(page.locator('.message')).toHaveCount(4);
 await page.screenshot({path:'test-results/v6-chat-workspace.png',fullPage:true});
});

test('V6 chat can create a skill draft and pause automation with recorded outcomes',async({page})=>{
 await page.getByRole('combobox',{name:'Select model',exact:true}).selectOption('fixture-a');
 await page.getByLabel('Message FOXORY').fill('Create a skill to check project evidence before drafting');
 await page.getByRole('button',{name:'Send message',exact:true}).click();
 await expect(page.locator('.message.assistant').last()).toContainText('Testing its read-only workflow now');
 await expect(page.getByRole('heading',{name:'Skill library',exact:true})).toHaveCount(0);
 await expect(page.getByLabel('Work progress')).toBeVisible();
 await page.getByLabel('Message FOXORY').fill('pause automation');
 await page.getByRole('button',{name:'Send message',exact:true}).click();
 await expect(page.locator('.message.assistant').last()).toContainText('Project automation paused');
 await expect(page.locator('.chat-action-receipt').last()).toContainText('paused');
 await expect(page.getByLabel('Message FOXORY')).toBeVisible();
});

test('V6 mobile tools preserve the chat workspace',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 await page.getByLabel('Message FOXORY').fill('MOBILE_DRAFT');
 await openTool(page,'Memory');
 await expect(page.getByRole('heading',{name:'Learned from our conversations',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Close chat panel',exact:true}).click();
 await expect(page.getByLabel('Message FOXORY')).toHaveValue('MOBILE_DRAFT');
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
 await page.screenshot({path:'test-results/v6-chat-mobile.png',fullPage:true});
});


test('chat executes a deliverable with a real download and persistent receipt',async({page})=>{
 await page.getByLabel('Message FOXORY').fill('Create a complete offer document EXECUTION_BROWSER');
 await page.getByRole('button',{name:'Send message',exact:true}).click();
 await expect(page.getByText('Created: Finished browser offer.',{exact:true})).toBeVisible();
 const downloadEvent=page.waitForEvent('download');await page.getByRole('button',{name:'Download MD',exact:true}).click();const file=await downloadEvent;expect(file.suggestedFilename()).toBe('Finished_browser_offer.md');
 await page.reload();await page.locator('.history-row > button').first().click();
 await expect(page.getByRole('button',{name:'Download MD',exact:true})).toBeVisible();
 await expect(page.getByText('Working on it…',{exact:true})).toHaveCount(0);
 await page.screenshot({path:'test-results/v61-chat-execution.png',fullPage:true});
});


test('automatic model choice is default, explained, and can be overridden',async({page})=>{
 const selector=page.getByLabel('Select model',{exact:true});await expect(selector).toHaveValue('auto');
 const requests:any[]=[];page.on('request',r=>{if(r.url().endsWith('/chat')&&r.method()==='POST')requests.push(r.postDataJSON())});
 await page.getByLabel('Message FOXORY').fill('Hello there');await page.getByRole('button',{name:'Send message',exact:true}).click();
 await expect(page.locator('.model-route').last()).toContainText('Auto · fixture-a · chat');expect(requests[0].model).toBe('auto');
 await selector.selectOption('fixture-b');await page.getByLabel('Message FOXORY').fill('Hello again');await page.getByRole('button',{name:'Send message',exact:true}).click();
 await expect(page.locator('.model-route').last()).toContainText('Manual · fixture-b');expect(requests[1].model).toBe('fixture-b');
 await page.reload();await expect(selector).toHaveValue('fixture-b');await selector.selectOption('auto');await page.reload();await expect(selector).toHaveValue('auto');
 await page.locator('.history-row > button').first().click();await expect(page.locator('.model-route').first()).toContainText('Auto · fixture-a');
 await page.screenshot({path:'test-results/v62-auto-models.png',fullPage:true});
});

test('V7 AI controls stay inside Chat and policy changes persist',async({page})=>{
 await openTool(page,'AI runtime');await expect(page.getByRole('heading',{name:'Always-on local AI',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Eco',exact:true}).click();await expect(page.getByRole('button',{name:'Eco',exact:true})).toHaveAttribute('aria-pressed','true');
 await page.getByLabel('Background AI enabled',{exact:true}).uncheck();await expect(page.getByRole('status').last()).toContainText('waiting for policy/budget');
 await page.reload();await openTool(page,'AI runtime');await expect(page.getByRole('button',{name:'Eco',exact:true})).toHaveAttribute('aria-pressed','true');
 await page.getByLabel('Background AI enabled',{exact:true}).check();await page.getByRole('button',{name:'Balanced',exact:true}).click();
 await page.getByRole('button',{name:'Close chat panel',exact:true}).click();await page.getByLabel('Message FOXORY').fill('use quality mode');await page.getByRole('button',{name:'Send message',exact:true}).click();
 await expect(page.locator('.message.assistant').last()).toContainText('Saved AI mode: quality');
 await page.getByRole('button',{name:'Balanced',exact:true}).click();
 await page.screenshot({path:'test-results/v7-ai-runtime.png',fullPage:true});
});
