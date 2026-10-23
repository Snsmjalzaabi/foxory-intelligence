import {test,expect} from '@playwright/test';

test.beforeEach(async({page})=>{
 await page.goto('/');
 await expect(page.getByRole('button',{name:/Sign in|Create administrator/})).toBeVisible();
 if(await page.getByLabel('Workspace bootstrap token').isVisible())await page.getByLabel('Workspace bootstrap token').fill('e2e-only-token-with-at-least-24-chars');
 await page.getByLabel('Username',{exact:true}).fill('e2e-owner');
 await page.getByLabel('Password',{exact:true}).fill('e2e-owner-password-123');
 await page.getByRole('button',{name:/Sign in|Create administrator/}).click();
 await expect(page.getByRole('heading',{name:'What will you build today?'})).toBeVisible({timeout:20000});
});

test('chat streams, persists, regenerates and exports through the real HTTP adapter',async({page})=>{
 await page.getByLabel('Message FOXORY').fill('Explain local ownership');
 await page.getByRole('button',{name:'Send message'}).click();
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
 await expect(page.locator('.document-answer')).toContainText('Test fixture response');
 await expect(page.locator('.document-answer')).toContainText('quarter.txt');
 await page.locator('input[type=file]').setInputFiles({name:'bad.json',mimeType:'application/json',buffer:Buffer.from('{')});
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
 await expect(page.locator('.job-detail')).toContainText('completed',{timeout:20000});
 await expect(page.locator('.job-detail')).toContainText('fixture-a · independent analysis');
 await expect(page.locator('.job-detail')).toContainText('fixture-b · independent analysis');
});

test('mobile navigation and theme work',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 await page.getByLabel('Open navigation').click();
 await page.locator('nav').getByRole('button',{name:'Settings',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Settings',exact:true})).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
 await page.screenshot({path:'test-results/settings-mobile.png',fullPage:true});
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
 test.setTimeout(60000);
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
 await expect(page.locator('.job-detail')).toContainText('completed',{timeout:20000});
 await expect(page.locator('.job-detail')).toContainText('Extractive evidence report');
 await page.getByRole('button',{name:'Check saved references'}).click();
 await expect(page.locator('.job-detail').getByRole('status')).toContainText('content hashes match');
 await page.locator('.source-card summary').first().click();
 await expect(page.locator('.source-card')).toContainText('Revenue was 123 units');
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
 await expect(page.getByRole('status')).toContainText('awaiting_approval',{timeout:30000});
 await page.getByRole('button',{name:'Approvals',exact:true}).click();
 await expect(page.getByText('Immutable approval context',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'approve action',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Allow project.create · consumed'})).toBeVisible({timeout:30000});
 await page.getByRole('button',{name:'Projects',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Browser agent project'})).toBeVisible();
});
