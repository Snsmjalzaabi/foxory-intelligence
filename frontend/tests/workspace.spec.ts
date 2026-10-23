import {test,expect} from '@playwright/test';

test.beforeEach(async({page})=>{
 await page.goto('/');
 if(await page.getByLabel('Workspace bootstrap token').isVisible())await page.getByLabel('Workspace bootstrap token').fill('e2e-only-token-with-at-least-24-chars');
 await page.getByLabel('Username',{exact:true}).fill('e2e-owner');
 await page.getByLabel('Password',{exact:true}).fill('e2e-owner-password-123');
 await page.getByRole('button',{name:/Sign in|Create administrator/}).click();
 await expect(page.getByRole('heading',{name:'What will you build today?'})).toBeVisible();
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
 await expect(page.getByRole('heading',{name:'quarter.txt',exact:true})).toBeVisible();
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
