const { chromium } = require('playwright');

async function setupAutomatedBrowser() {
  const userDataDir = 'C:\\Users\\deann\\.clawdbot\\browser\\automation';
  const context = await chromium.launchPersistentContext(userDataDir, {
    channel: 'chrome',
    headless: false,
    args: [
      '--enable-automation',
      '--enable-chrome-browser-cloud-management',
      '--load-extension=C:\\Users\\deann\\.clawdbot\\extensions\\clawdbot'
    ]
  });
  
  const page = await context.newPage();
  
  // Wait for extension to be ready
  const targets = context.pages();
  const backgroundTarget = targets.find(t => t.url().startsWith('chrome-extension://'));
  
  if (backgroundTarget) {
    await backgroundTarget.evaluate(() => {
      chrome.runtime.sendMessage({ type: 'ATTACH_TAB' });
    });
  }
  
  return { context, page };
}

module.exports = { setupAutomatedBrowser };