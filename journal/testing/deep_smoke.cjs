// Offline browser acceptance for Issue #18; no server or network access.
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const { chromium } = require("playwright");

(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: process.env.CHROME_EXECUTABLE || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    args: ["--no-sandbox"],
  });
  const root = path.resolve(__dirname, "../site");
  const home = pathToFileURL(path.join(root, "index.html")).href;
  const assessment = pathToFileURL(path.join(root, "assessments", "2610.25802.html")).href;
  for (const [name, width, height] of [["desktop", 1440, 1000], ["mobile", 390, 844], ["reflow-320", 320, 700]]) {
    const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1 });
    await page.goto(home);
    const links = page.locator("a.deep-full-link");
    if (await links.count() !== 1) throw Error("Expected exactly one full-assessment link");
    if (await page.locator("[data-copy-prompt]").count() !== 8) throw Error("Missing journal copy prompts");
    await links.click();
    if (!page.url().endsWith("2610.25802.html")) throw Error("Full assessment navigation failed");
    if (await page.locator("h1").count() !== 1) throw Error("Missing unique accessible H1");
    if (await page.locator("nav.deep-toc a").count() !== 8) throw Error("Table of contents missing");
    if (await page.locator("a[href^='https://arxiv.org/pdf/2610.25802v2#page=']").count() < 12)
      throw Error("Source-to-claim anchor links missing");
    const size = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth }));
    if (size.scroll > size.client + 1) throw Error("Horizontal overflow at " + width + ": " + JSON.stringify(size));
    await page.locator("nav.deep-toc a[href='#5-falsifiable-read-only-validation-protocol']").click();
    if (!page.url().includes("#5-falsifiable-read-only-validation-protocol")) throw Error("Internal navigation failed");
    if (name !== "reflow-320") await page.screenshot({ path: path.join(root, "..", "previews", "deep-" + name + ".png"), fullPage: true });
    console.log("PASS", name, "reflow", JSON.stringify(size), "sections", await page.locator("article h2").count());
    await page.close();
  }
  // Zoom/reflow approximation: effective viewport widths 640 and 320 for 200/400% of 1280 CSS px.
  for (const [zoom, width] of [["200%", 640], ["400%", 320]]) {
    const page = await browser.newPage({ viewport: { width, height: 900 } });
    await page.goto(assessment);
    const size = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth }));
    if (size.scroll > size.client + 1) throw Error("Zoom-equivalent reflow " + zoom + ": " + JSON.stringify(size));
    console.log("PASS", zoom, "effective-width reflow");
    await page.close();
  }
  const page = await browser.newPage();
  await page.goto(home);
  await page.locator("button.feature-copy[data-id='2610.25802']").click();
  const open = await page.locator("#prompt-dialog").evaluate(el => el.open);
  if (open) {
    await page.keyboard.press("Escape");
    if (await page.locator("#prompt-dialog").evaluate(el => el.open)) throw Error("Dialog keyboard close failed");
    console.log("PASS copy-prompt fallback dialogue and Escape");
  } else {
    await page.getByText("Research prompt copied. Paste it into a ChatGPT conversation.").waitFor({ timeout: 3000 });
    console.log("PASS copy-prompt native clipboard success");
  }
  await browser.close();
})().catch(error => { console.error(error); process.exitCode = 1; });
