import { chromium } from 'playwright'

async function openBrowser() {
  const browser = await chromium.launch({ headless: false })
  const page = await browser.newPage()
  await page.goto('http://localhost:5176/')
  
  console.log('Browser opened at http://localhost:5176/')
  console.log('Press Ctrl+C to close the browser')
  
  // Keep browser open
  await new Promise(() => {})
}

openBrowser().catch(console.error)

