/* Export one local poster to PNG and/or a single-page vector PDF. */
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { pathToFileURL } = require("node:url");

function getChromium() {
  for (const name of ["playwright", "playwright-core"]) {
    try {
      return require(name).chromium;
    } catch (error) {
      if (error.code !== "MODULE_NOT_FOUND") throw error;
    }
  }
  throw new Error("Provide Playwright or playwright-core in the Node module search path.");
}

function browserPath(chromium) {
  if (process.env.INFOGRAPHIC_BROWSER) return process.env.INFOGRAPHIC_BROWSER;
  const programFiles = process.env.PROGRAMFILES || "C:/Program Files";
  const candidates = [
    chromium.executablePath(),
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    path.join(os.homedir(), "Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/usr/bin/google-chrome",
    path.join(programFiles, "Google/Chrome/Application/chrome.exe"),
  ];
  return candidates.find(candidate => fs.existsSync(candidate));
}

async function main() {
  const [input, ...outputs] = process.argv.slice(2);
  const supported = file => /\.(pdf|png)$/i.test(file);
  if (!input || !outputs.length || !outputs.every(supported)) {
    throw new Error("Usage: node export.cjs poster.html [poster.png] [poster.pdf]");
  }
  const source = path.resolve(input);
  fs.accessSync(source, fs.constants.R_OK);
  const chromium = getChromium();
  const executablePath = browserPath(chromium);
  const browser = await chromium.launch({ headless: true, executablePath });
  try {
    const context = await browser.newContext({
      viewport: { width: 1200, height: 900 }, deviceScaleFactor: 2, offline: true,
    });
    const page = await context.newPage();
    await page.goto(pathToFileURL(source).href);
    await page.evaluate(() => document.fonts.ready);
    const poster = page.locator("#poster");
    await poster.waitFor();
    await poster.evaluate(element => element.classList.add("static-export"));
    for (const file of outputs) {
      if (path.extname(file).toLowerCase() === ".png") {
        await page.emulateMedia({ media: "screen" });
        await poster.screenshot({ path: file, type: "png", animations: "disabled" });
      } else {
        await page.emulateMedia({ media: "print" });
        const { width, height } = await poster.boundingBox();
        await page.pdf({
          path: file, width: Math.ceil(width) + "px", height: (Math.ceil(height) + 2) + "px",
          printBackground: true, margin: { top: 0, bottom: 0, left: 0, right: 0 },
        });
      }
    }
  } finally {
    await browser.close();
  }
}

main().catch(error => {
  process.stderr.write(error.message + "\n");
  process.exitCode = 1;
});
