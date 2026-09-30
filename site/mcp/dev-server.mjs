import { createServer } from "node:http";
import { readFile, stat } from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";

const site = path.resolve(import.meta.dirname, "..");
const assets = path.resolve(site, process.env.MCP_ASSETS_DIR ?? "dist-mcp/client");
const workerPath = path.resolve(site, process.env.MCP_WORKER_ENTRY ?? "dist-mcp/server/index.js");
const { default: worker } = await import(pathToFileURL(workerPath).href);
const port = Number(process.env.PORT ?? 8787);
const mime = { ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8", ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml", ".png": "image/png", ".ico": "image/x-icon" };

const binding = {
  async fetch(request) {
    let name;
    try { name = decodeURIComponent(new URL(request.url).pathname); }
    catch { return new Response("Bad path", { status: 400 }); }
    const file = path.resolve(assets, `.${name}`);
    if (file !== assets && !file.startsWith(`${assets}${path.sep}`)) return new Response("Forbidden", { status: 403 });
    try {
      const actual = (await stat(file)).isDirectory() ? path.join(file, "index.html") : file;
      const bytes = await readFile(actual);
      return new Response(bytes, { headers: { "Content-Type": mime[path.extname(actual)] ?? "application/octet-stream" } });
    } catch {
      try { return new Response(await readFile(path.join(assets, "index.html")), { headers: { "Content-Type": mime[".html"] } }); }
      catch { return new Response("Not found", { status: 404 }); }
    }
  },
};

createServer(async (incoming, outgoing) => {
  try {
    const chunks = [];
    let size = 0;
    for await (const chunk of incoming) {
      size += chunk.length;
      if (size > 1_000_000) { outgoing.writeHead(413).end(); return; }
      chunks.push(chunk);
    }
    const request = new Request(`http://127.0.0.1:${port}${incoming.url}`, {
      method: incoming.method, headers: incoming.headers,
      body: chunks.length ? Buffer.concat(chunks) : undefined,
    });
    const response = await worker.fetch(request, { ASSETS: binding });
    outgoing.writeHead(response.status, Object.fromEntries(response.headers));
    outgoing.end(Buffer.from(await response.arrayBuffer()));
  } catch (error) {
    console.error("Local MCP request failed", error);
    outgoing.writeHead(500).end("Internal error");
  }
}).listen(port, "127.0.0.1", () => console.log(`Local MCP server: http://127.0.0.1:${port}/mcp`));
