import { spawn } from "node:child_process";
import { access, mkdtemp, mkdir, readFile, readdir, rm, writeFile } from "node:fs/promises";
import { constants } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import process from "node:process";
import ExcelJS from "@protobi/exceljs";

const siteRoot = resolve(import.meta.dirname, "..");
const outputDirectory = resolve(siteRoot, "public/guide");
const defaultBaseUrl = "http://127.0.0.1:4174";
const baseUrl = (process.env.GUIDE_BASE_URL ?? defaultBaseUrl).replace(/\/$/, "");
const chromeCandidates = [
  process.env.GUIDE_CHROME_PATH,
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "/Applications/Chromium.app/Contents/MacOS/Chromium",
  "/usr/bin/google-chrome",
  "/usr/bin/chromium",
].filter(Boolean);

const wait = (milliseconds) => new Promise((resolveWait) => setTimeout(resolveWait, milliseconds));

async function findChrome() {
  for (const candidate of chromeCandidates) {
    try {
      await access(candidate, constants.X_OK);
      return candidate;
    } catch { /* Try the next known location. */ }
  }
  throw new Error("Chrome/Chromium が見つかりません。GUIDE_CHROME_PATH で実行ファイルを指定してください。");
}

async function waitForHttp(url, attempts = 100) {
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    try {
      const response = await fetch(url);
      if (response.ok) return;
    } catch { /* The local server is still starting. */ }
    await wait(100);
  }
  throw new Error(`ローカルサイトを開けませんでした: ${url}`);
}

async function startVite() {
  if (process.env.GUIDE_BASE_URL) {
    await waitForHttp(`${baseUrl}/search`);
    return null;
  }
  const sync = spawn(process.execPath, [resolve(siteRoot, "scripts/sync-site-data.mjs")], {
    cwd: siteRoot,
    stdio: ["ignore", "inherit", "inherit"],
  });
  const syncCode = await new Promise((resolveCode, reject) => {
    sync.once("error", reject);
    sync.once("exit", resolveCode);
  });
  if (syncCode !== 0) throw new Error(`Site-data の同期に失敗しました（終了コード ${syncCode}）。`);

  const vite = spawn(resolve(siteRoot, "node_modules/.bin/vite"), [
    "--host", "127.0.0.1", "--port", new URL(baseUrl).port, "--strictPort",
  ], { cwd: siteRoot, stdio: ["ignore", "inherit", "inherit"] });
  await waitForHttp(`${baseUrl}/search`);
  return vite;
}

async function startChrome(executable, profileDirectory) {
  const chrome = spawn(executable, [
    "--headless=new",
    "--disable-gpu",
    "--hide-scrollbars",
    "--remote-debugging-port=0",
    `--user-data-dir=${profileDirectory}`,
    "--no-first-run",
    "--no-default-browser-check",
    "--window-size=1440,1000",
    "about:blank",
  ], { stdio: ["ignore", "ignore", "pipe"] });

  const websocketUrl = await new Promise((resolveUrl, reject) => {
    const timeout = setTimeout(() => reject(new Error("Chrome のデバッグ接続を開始できませんでした。")), 15_000);
    chrome.once("error", reject);
    chrome.stderr.setEncoding("utf8");
    chrome.stderr.on("data", (chunk) => {
      const match = chunk.match(/DevTools listening on (ws:\/\/[^\s]+)/);
      if (match) {
        clearTimeout(timeout);
        resolveUrl(match[1]);
      }
    });
  });
  return { chrome, websocketUrl };
}

class CdpClient {
  constructor(websocket) {
    this.websocket = websocket;
    this.sequence = 0;
    this.pending = new Map();
    websocket.addEventListener("message", (event) => {
      const message = JSON.parse(String(event.data));
      if (!message.id) return;
      const callback = this.pending.get(message.id);
      if (!callback) return;
      this.pending.delete(message.id);
      if (message.error) callback.reject(new Error(`${callback.method}: ${message.error.message}`));
      else callback.resolve(message.result);
    });
  }

  static async connect(url) {
    const websocket = new WebSocket(url);
    await new Promise((resolveOpen, reject) => {
      websocket.addEventListener("open", resolveOpen, { once: true });
      websocket.addEventListener("error", reject, { once: true });
    });
    return new CdpClient(websocket);
  }

  send(method, params = {}, sessionId = undefined) {
    const id = ++this.sequence;
    return new Promise((resolveResult, reject) => {
      this.pending.set(id, { method, resolve: resolveResult, reject });
      this.websocket.send(JSON.stringify({ id, method, params, ...(sessionId ? { sessionId } : {}) }));
    });
  }

  close() { this.websocket.close(); }
}

async function createPage(client) {
  const { targetId } = await client.send("Target.createTarget", { url: "about:blank" });
  const { sessionId } = await client.send("Target.attachToTarget", { targetId, flatten: true });
  await client.send("Page.enable", {}, sessionId);
  await client.send("Runtime.enable", {}, sessionId);
  await client.send("Emulation.setDeviceMetricsOverride", {
    width: 1440,
    height: 1000,
    deviceScaleFactor: 1,
    mobile: false,
  }, sessionId);
  return sessionId;
}

async function evaluate(client, sessionId, expression) {
  const response = await client.send("Runtime.evaluate", {
    expression,
    awaitPromise: true,
    returnByValue: true,
  }, sessionId);
  if (response.exceptionDetails) {
    throw new Error(response.exceptionDetails.exception?.description ?? "ブラウザ内の評価に失敗しました。");
  }
  return response.result.value;
}

async function navigate(client, sessionId, path) {
  await client.send("Page.navigate", { url: `${baseUrl}${path}` }, sessionId);
  for (let attempt = 0; attempt < 100; attempt += 1) {
    const ready = await evaluate(client, sessionId, `document.readyState === "complete" && Boolean(document.querySelector("#app main"))`)
      .catch(() => false);
    if (ready) {
      await wait(150);
      return;
    }
    await wait(100);
  }
  throw new Error(`画面の読み込みが完了しませんでした: ${path}`);
}

async function waitForExpression(client, sessionId, expression, label) {
  for (let attempt = 0; attempt < 100; attempt += 1) {
    if (await evaluate(client, sessionId, expression).catch(() => false)) return;
    await wait(100);
  }
  throw new Error(`${label}を確認できませんでした。`);
}

function unionRectExpression(selectors) {
  return `(() => {
    const elements = ${JSON.stringify(selectors)}.map((selector) => document.querySelector(selector));
    if (elements.some((element) => !element)) return null;
    const rects = elements.map((element) => element.getBoundingClientRect());
    const x = Math.min(...rects.map((rect) => rect.left)) + scrollX;
    const y = Math.min(...rects.map((rect) => rect.top)) + scrollY;
    const right = Math.max(...rects.map((rect) => rect.right)) + scrollX;
    const bottom = Math.max(...rects.map((rect) => rect.bottom)) + scrollY;
    return { x, y, width: right - x, height: bottom - y };
  })()`;
}

async function capture(client, sessionId, filename, rectExpression, padding = 24, maxHeight = null) {
  const rect = await evaluate(client, sessionId, rectExpression);
  if (!rect || rect.width <= 0 || rect.height <= 0) throw new Error(`${filename} の撮影範囲を取得できませんでした。`);
  const clip = {
    x: Math.max(0, rect.x - padding),
    y: Math.max(0, rect.y - padding),
    width: Math.min(1440, rect.width + padding * 2),
    height: Math.min(rect.height + padding * 2, maxHeight ?? Number.POSITIVE_INFINITY),
    scale: 1,
  };
  const { data } = await client.send("Page.captureScreenshot", {
    format: "png",
    fromSurface: true,
    captureBeyondViewport: true,
    clip,
  }, sessionId);
  await writeFile(resolve(outputDirectory, filename), Buffer.from(data, "base64"));
  console.log(`Captured ${filename} (${Math.round(clip.width)}x${Math.round(clip.height)})`);
}

const selectorRect = (selector) => unionRectExpression([selector]);
const groupRect = (university) => `(() => {
  const button = [...document.querySelectorAll("button[data-university-toggle]")]
    .find((item) => item.dataset.universityToggle === ${JSON.stringify(university)});
  const element = button?.closest(".university-group");
  if (!element) return null;
  const rect = element.getBoundingClientRect();
  return { x: rect.left + scrollX, y: rect.top + scrollY, width: rect.width, height: rect.height };
})()`;

async function expandUniversity(client, sessionId, university) {
  const clicked = await evaluate(client, sessionId, `(() => {
    const button = [...document.querySelectorAll("button[data-university-toggle]")]
      .find((item) => item.dataset.universityToggle === ${JSON.stringify(university)});
    if (!button) return false;
    if (button.getAttribute("aria-expanded") !== "true") button.click();
    return true;
  })()`);
  if (!clicked) throw new Error(`${university} の結果グループが見つかりません。`);
  await wait(100);
}

async function addCandidate(client, sessionId, recordId) {
  const clicked = await evaluate(client, sessionId, `(() => {
    const button = document.querySelector('button[data-candidate-toggle*="${recordId}"]');
    if (!button) return false;
    if (button.getAttribute("aria-pressed") !== "true") button.click();
    return true;
  })()`);
  if (!clicked) throw new Error(`${recordId} の候補追加ボタンが見つかりません。`);
  await waitForExpression(
    client,
    sessionId,
    `document.querySelector('button[data-candidate-toggle*="${recordId}"]')?.getAttribute("aria-pressed") === "true"`,
    `${recordId} の保存状態`,
  );
}

async function verifyWorkbook(path) {
  const workbook = new ExcelJS.Workbook();
  await workbook.xlsx.load(await readFile(path));
  const sheet = workbook.getWorksheet("候補リスト");
  if (!sheet || sheet.rowCount !== 3) throw new Error("Excel出力がヘッダー1行と候補2件になっていません。");
  const universities = [sheet.getCell("A2").text, sheet.getCell("A3").text].sort();
  if (universities.join("|") !== ["北里大学", "名古屋大学"].sort().join("|")) {
    throw new Error(`Excel出力の大学が一致しません: ${universities.join("、")}`);
  }
}

async function main() {
  await mkdir(outputDirectory, { recursive: true });
  const workingDirectory = await mkdtemp(join(tmpdir(), "early-admissions-guide-"));
  const profileDirectory = resolve(workingDirectory, "chrome-profile");
  const downloadDirectory = resolve(workingDirectory, "downloads");
  await mkdir(downloadDirectory, { recursive: true });
  const vite = await startVite();
  let chrome;
  let client;
  try {
    const launched = await startChrome(await findChrome(), profileDirectory);
    chrome = launched.chrome;
    client = await CdpClient.connect(launched.websocketUrl);
    const sessionId = await createPage(client);
    await client.send("Browser.setDownloadBehavior", {
      behavior: "allow",
      downloadPath: downloadDirectory,
      eventsEnabled: true,
    });

    await navigate(client, sessionId, "/search?university=%E5%90%8D%E5%8F%A4%E5%B1%8B%E5%A4%A7%E5%AD%A6");
    await evaluate(client, sessionId, "localStorage.clear(); true");
    await capture(client, sessionId, "university-search-nagoya.png", unionRectExpression([".form-intro", "#search-form fieldset:nth-of-type(1)"]));

    const academicQuery = "/search?academic_field_v2=natural_sciences&academic_subfield_v2=natural_sciences%3Abiology&academic_field_v2=life_sciences&academic_field_v2=pharmacy";
    await navigate(client, sessionId, academicQuery);
    await capture(client, sessionId, "academic-field-selection.png", unionRectExpression([".academic-field-section:nth-of-type(2)", ".academic-field-section:nth-of-type(3)"]));

    const scenarioQuery = "academic_field_v2=natural_sciences&academic_subfield_v2=natural_sciences%3Abiology&academic_field_v2=life_sciences&academic_field_v2=pharmacy&common_test_required=No&research_requirement_required=Yes&english_requirement_status=not_required";
    await navigate(client, sessionId, `/search?${scenarioQuery}`);
    await capture(client, sessionId, "research-and-test-filters.png", unionRectExpression(["#search-form fieldset:nth-of-type(5)", "#search-form fieldset:nth-of-type(8)"]));

    await navigate(client, sessionId, "/search?grade_requirement=required&overall_gpa=3.8&prefecture_membership=%E6%9D%B1%E4%BA%AC%E9%83%BD&prefecture_membership=%E7%A5%9E%E5%A5%88%E5%B7%9D%E7%9C%8C");
    await evaluate(client, sessionId, "document.querySelector('#prefecture-details').open = true; true");
    await capture(client, sessionId, "grade-and-prefecture-filters.png", unionRectExpression(["#search-form fieldset:nth-of-type(9)", "#search-form fieldset:nth-of-type(10)"]), 24, 850);

    await navigate(client, sessionId, `/results?${scenarioQuery}`);
    await waitForExpression(client, sessionId, "document.querySelector('.result-count')?.textContent?.includes('14件')", "14件の検索結果");
    await expandUniversity(client, sessionId, "東京農工大学");
    await capture(client, sessionId, "search-results-sail.png", groupRect("東京農工大学"));

    await navigate(client, sessionId, "/results?university=%E5%90%8D%E5%8F%A4%E5%B1%8B%E5%A4%A7%E5%AD%A6&common_test_required=No&research_requirement_required=Yes");
    await expandUniversity(client, sessionId, "名古屋大学");
    await addCandidate(client, sessionId, "NU-2027-NCT-02");
    await capture(client, sessionId, "save-nagoya.png", groupRect("名古屋大学"));

    await navigate(client, sessionId, "/results?university=%E5%8C%97%E9%87%8C%E5%A4%A7%E5%AD%A6&common_test_required=No&research_requirement_required=Yes&english_requirement_status=not_required");
    await expandUniversity(client, sessionId, "北里大学");
    await addCandidate(client, sessionId, "KITA-2027-PH-03");
    await capture(client, sessionId, "save-kitasato.png", groupRect("北里大学"));

    await navigate(client, sessionId, "/candidates");
    await expandUniversity(client, sessionId, "名古屋大学");
    await expandUniversity(client, sessionId, "北里大学");
    await waitForExpression(client, sessionId, "document.querySelector('#candidate-selection-count')?.textContent === '2件中 2件選択'", "候補2件の選択状態");
    await capture(client, sessionId, "saved-admissions.png", selectorRect("#main"));

    const excelClicked = await evaluate(client, sessionId, `(() => {
      const button = document.querySelector('button[data-candidate-export="xlsx"]');
      if (!button || button.disabled) return false;
      button.click();
      return true;
    })()`);
    if (!excelClicked) throw new Error("Excel出力ボタンを実行できませんでした。");
    await waitForExpression(client, sessionId, "document.querySelector('#candidate-export-status')?.textContent === '2件を出力しました。'", "Excel出力完了表示");
    let downloadedPath = "";
    for (let attempt = 0; attempt < 100; attempt += 1) {
      const files = await readdir(downloadDirectory);
      const name = files.find((file) => file.endsWith(".xlsx") && !file.endsWith(".crdownload"));
      if (name) { downloadedPath = resolve(downloadDirectory, name); break; }
      await wait(100);
    }
    if (!downloadedPath) throw new Error("生成されたExcelファイルを確認できませんでした。");
    await verifyWorkbook(downloadedPath);
    await capture(client, sessionId, "excel-download.png", unionRectExpression([".candidate-toolbar", ".university-group:nth-of-type(1)"]));
    console.log(`Verified Excel export: ${downloadedPath} (2 candidates)`);
  } finally {
    client?.close();
    chrome?.kill("SIGTERM");
    vite?.kill("SIGTERM");
    await rm(workingDirectory, { recursive: true, force: true });
  }
}

await main();
