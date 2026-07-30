import { writeFile } from 'fs/promises'
import { join } from 'path'
import { chromium } from 'playwright'

async function testBrowser() {
  console.log('Launching browser...')
  const browser = await chromium.launch({ headless: false })
  const page = await browser.newPage()
  
  console.log('Navigating to http://localhost:5176/...')
  await page.goto('http://localhost:5176/', { waitUntil: 'networkidle' })
  
  console.log('Page loaded! Taking screenshot...')
  const screenshot = await page.screenshot({ fullPage: true })
  
  const screenshotPath = join(process.cwd(), 'screenshot.png')
  await writeFile(screenshotPath, screenshot)
  console.log(`Screenshot saved to: ${screenshotPath}`)
  
  // Get page title
  const title = await page.title()
  console.log(`Page title: ${title}`)
  
  // Wait a bit so user can see the browser
  console.log('Browser will stay open for 5 seconds...')
  await page.waitForTimeout(5000)
  
  await browser.close()
  console.log('Browser closed. Test complete!')
}

testBrowser().catch((error) => {
  console.error('Error:', error)
  process.exit(1)
})

