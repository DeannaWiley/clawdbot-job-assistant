const { chromium } = require('playwright');
const fs = require('fs').promises;

async function convertToPDF(htmlContent, outputPath) {
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();
  
  // Load custom CSS for PDF styling
  const css = `
    body {
      font-family: 'Arial', sans-serif;
      line-height: 1.6;
      max-width: 800px;
      margin: 0 auto;
      padding: 40px;
    }
    h1, h2, h3 { color: #2c3e50; }
    .header { margin-bottom: 30px; }
    .contact-info { color: #34495e; }
  `;
  
  // Wrap content in styled HTML
  const wrappedContent = `
    <!DOCTYPE html>
    <html>
      <head>
        <style>${css}</style>
      </head>
      <body>${htmlContent}</body>
    </html>
  `;
  
  await page.setContent(wrappedContent);
  await page.pdf({ path: outputPath, format: 'Letter', margin: { top: '0.5in', bottom: '0.5in', left: '0.5in', right: '0.5in' } });
  await browser.close();
}

module.exports = { convertToPDF };