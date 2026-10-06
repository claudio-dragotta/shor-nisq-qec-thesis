// Cattura i pannelli della demo con tema chiaro. Uso: node cattura.mjs [chiaro|scuro] [cartella]
import { chromium } from "playwright";
import fs from "node:fs";

const [tema = "chiaro", out = "out"] = process.argv.slice(2);
fs.mkdirSync(out, { recursive: true });
const browser = await chromium.launch({ headless: true, channel: "chromium" });
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 2 });
page.on("pageerror", (e) => console.error("pageerror:", e.message));
await page.goto("http://localhost:8501/?lang=it");
await page.waitForLoadState("networkidle");
if (tema === "chiaro") await page.addStyleTag({ path: "tema_chiaro.css" });

await page.click("#noiseTab");
await page.click("#viewCompareBtn");
for (let i = 0; i < 40; i++) {
  const c = (await page.textContent("#noiseStageCounter")).trim();
  if (/^6\s*\/\s*6$/.test(c)) break;
  if (await page.isEnabled("#noiseNextBtn")) await page.click("#noiseNextBtn");
  await page.waitForTimeout(1500);
}
console.log("contatore:", (await page.textContent("#noiseStageCounter")).trim());
await page.waitForTimeout(1500);
const scurisci = () => page.evaluate(() => {
  for (const el of document.querySelectorAll("svg [stroke], svg [fill]")) {
    for (const a of ["stroke", "fill"]) {
      const v = el.getAttribute(a);
      if (v && /^hsl\(/.test(v)) el.setAttribute(a, v.replace(/(\d+)% (\d+)%\)/, "$1% 40%)"));
    }
  }
});
if (tema === "chiaro") await scurisci();
await page.locator("#noiseStageView").screenshot({ path: `${out}/demo_confronto_ideale_rumore.png` });
if (await page.isHidden("#noiseDetail")) await page.click("#noiseDetailBtn");
await page.waitForTimeout(800);
await page.locator(".anatomy-panel .anatomy-scroller").scrollIntoViewIfNeeded();
await page.locator(".anatomy-panel .anatomy-scroller").screenshot({ path: `${out}/demo_dove_entra_il_rumore.png` });
await browser.close();
