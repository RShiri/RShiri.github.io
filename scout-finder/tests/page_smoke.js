// Browser smoke test for scout-finder/index.html.
//   python -m http.server 8765            (from the repo root)
//   node scout-finder/tests/page_smoke.js [http://localhost:8765/scout-finder/]
// Needs the playwright package; CHROME=/path/to/chrome picks a browser binary.
// Checks both looks, Hebrew and a phone width: a profile renders, similar players and the
// finder fill, the head-to-head works, there are no page errors, and the page's own
// similarity ranking agrees with the pipeline's precomputed lists.
const { chromium } = require("playwright");
const BASE = process.argv[2] || "http://localhost:8765/scout-finder/";
const OUT = process.env.SHOTS;  // optional folder for screenshots

(async () => {
  const browser = await chromium.launch(process.env.CHROME ? { executablePath: process.env.CHROME } : {});
  const fails = [];
  const check = (ok, msg) => { if (!ok) fails.push(msg); };
  const runs = [
    ["c-en", "?style=c&lang=en", 1280, "#fotmob%3A1467236"],
    ["a-he", "?style=a&lang=he", 1280, "#fotmob%3A113318"],
    ["mobile", "?style=c&lang=en", 390, ""],
  ];
  for (const [name, query, width, hash] of runs) {
    const page = await browser.newPage({ viewport: { width, height: 900 } });
    const errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    page.on("console", (m) => { if (m.type() === "error" && !/fonts\.g|favicon|seasons\.json|ERR_/.test(m.text())) errors.push(m.text()); });
    await page.goto(BASE + query + hash);
    await page.waitForSelector("#app:not([hidden]) #card h2", { timeout: 20000 });
    const s = await page.evaluate(() => ({
      name: document.querySelector("#card h2").textContent,
      bars: document.querySelectorAll("#card .bar").length,
      similar: document.querySelectorAll("#similar tbody tr").length,
      finder: document.querySelectorAll("#finder tbody tr").length,
      h2h: document.querySelectorAll("#h2h .h2h-row").length,
      note: document.querySelectorAll("#note p").length,
      overflow: document.documentElement.scrollWidth > window.innerWidth + 1,
    }));
    check(s.bars >= 3 && s.similar === 10 && s.finder > 0 && s.h2h >= 3 && s.note >= 2, `${name}: page incomplete ${JSON.stringify(s)}`);
    check(!s.overflow, `${name}: page scrolls sideways`);
    if (name === "c-en") {
      // Search, open, then compare through the head-to-head picker.
      await page.fill("#q", "pedri"); await page.keyboard.press("Enter");
      await page.waitForFunction(() => document.querySelector("#card h2").textContent === "Pedri");
      await page.fill("#q2", "rice"); await page.keyboard.press("Enter");
      await page.waitForFunction(() => /Rice/.test(document.querySelector("#h2h .side.b").textContent));
      check(decodeURIComponent(await page.evaluate(() => location.hash)).includes("~fotmob:654096"), "c-en: compare not in the URL");
      // The page's similarity must reproduce the pipeline's top-8 (rounding of per90 aside).
      const agree = await page.evaluate(async () => {
        const d = await (await fetch("data/universe_2025-26.json")).json();
        const sample = d.players.filter((_, i) => i % 97 === 0);
        let same = 0, total = 0;
        for (const p of sample) {
          location.hash = "#" + encodeURIComponent(p.id);
          await new Promise((r) => setTimeout(r, 30));
          const shown = [...document.querySelectorAll("#similar tbody tr")].slice(0, 8).map((tr) => tr.dataset.id);
          const want = p.similar.map((x) => x.id);
          total += want.length; same += want.filter((id) => shown.includes(id)).length;
        }
        return same / total;
      });
      check(agree >= 0.95, `c-en: page similarity agrees with the pipeline on only ${(agree * 100).toFixed(1)}%`);
      console.log(`similarity agreement with pipeline: ${(agree * 100).toFixed(1)}%`);
    }
    check(!errors.length, `${name}: errors ${errors.join(" | ")}`);
    if (OUT) await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: true });
    console.log(name, JSON.stringify(s));
    await page.close();
  }
  await browser.close();
  if (fails.length) { console.error("FAIL\n" + fails.join("\n")); process.exit(1); }
  console.log("OK");
})();
