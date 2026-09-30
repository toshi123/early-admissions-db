# `ea` Worker deployment setup

The `codex/mcp-v0.1` implementation can be built as an independent Cloudflare Worker. It does not update the existing Site project or canonical admissions data.

## Cloudflare Workers Builds fields

| Field | Value |
| --- | --- |
| Worker name | `ea` |
| Git provider | GitHub |
| Repository | `toshi123/early-admissions-db` |
| Production branch | `master` after this branch is reviewed and merged |
| Root directory | `site` |
| Build command | `npm run build:ea` |
| Deploy command | `npm run deploy:ea` |
| Wrangler configuration | `site/wrangler.jsonc` (automatically found from the root directory) |
| Node.js | 22 (`site/.nvmrc`) |
| Runtime secrets or variables | None |

The MCP endpoint will be `/mcp` on the `ea` Worker URL. The default `workers.dev` hostname depends on the Cloudflare account. `workers_dev: true` is set; no custom domain or route is configured. The Worker serves its own frozen copy of the public Site assets for data access and detail links, without altering the existing Site deployment.

Workers Builds installs dependencies from `site/package-lock.json`. The `build:ea` script checks the TypeScript MCP implementation, verifies the checked-in public client archive by SHA-256 and every Site-data receipt, and bundles `mcp/worker.ts` to `site/dist-ea/index.js`. The `deploy:ea` script runs the pinned Wrangler version against `site/wrangler.jsonc`.

`site/mcp/frozen-client-v0.1.tar.gz` is a generated snapshot from the validated local `site/dist-mcp/client` build. It contains Site-data build `865009a49ad663caf924` with 6,699 confirmed rows. Generate it with `python3 scripts/package-ea-client.py` after `npm run build:mcp`. The packager excludes `_redirects` because Wrangler's `single-page-application` fallback handles routing, as well as `.DS_Store`, AppleDouble `._*`, and source maps. It writes a deterministic USTAR archive with no extended attributes and updates the archive hash and asset count in `frozen-client-v0.1.json`. The `build:ea` script rejects forbidden files in the extracted assets. Do not edit records inside the archive by hand.

Cloudflare's **Save and Deploy** action deploys the Worker. Keep the Git integration unconnected until production deployment is authorized. This branch has not been merged into `master` or deployed.
