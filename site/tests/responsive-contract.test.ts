import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const css = readFileSync(join(process.cwd(), "src/styles.css"), "utf8");

describe("responsive search and compact results contract", () => {
  it("keeps a dedicated mobile layout and touch-sized form actions", () => {
    expect(css).toContain("@media (max-width: 620px)");
    expect(css).toContain("min-height: 44px");
    expect(css).toContain(".result-card { padding: .68rem .75rem .72rem; }");
  });

  it("positions the live count at the desktop edge and as a compact mobile bar", () => {
    expect(css).toContain(".floating-live-summary {");
    expect(css).toContain("position: fixed");
    expect(css).toContain("right: max(1rem, calc((100vw - 1120px) / 2))");
    expect(css).toContain("left: 50%");
    expect(css).toContain("max-width: calc(100vw - 1.5rem)");
    expect(css).toContain(".floating-live-summary { transition: none; }");
  });
});
