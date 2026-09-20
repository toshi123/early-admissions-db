import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const css = readFileSync(join(process.cwd(), "src/styles.css"), "utf8");

describe("responsive search and compact results contract", () => {
  it("keeps a dedicated mobile layout and touch-sized form actions", () => {
    expect(css).toContain("@media (max-width: 620px)");
    expect(css).toContain(".choice { min-height: 44px");
    expect(css).toContain(".button { min-height: 48px");
    expect(css).toContain(".result-card { padding: .875rem .75rem; }");
  });

  it("positions the live count at the desktop edge and as a compact mobile bar", () => {
    expect(css).toContain(".floating-live-summary {");
    expect(css).toContain("position: fixed");
    expect(css).toContain("right: max(1rem, calc((100vw - 1120px) / 2))");
    expect(css).toContain("left: 50%");
    expect(css).toContain("max-width: calc(100vw - 1.5rem)");
    expect(css).toContain(".floating-live-summary { transition: none; }");
  });

  it("uses the fixed DADS focus colors and horizontal-menu current marker", () => {
    expect(css).toContain("--yellow-300: #ffd43d");
    expect(css).toContain("outline: 4px solid #000");
    expect(css).toContain("box-shadow: 0 0 0 2px var(--yellow-300)");
    expect(css).toContain('.global-nav__link[aria-current="page"]::after');
    expect(css).toContain("border-bottom: 4px solid var(--blue-900)");
  });

  it("keeps mobile navigation and search controls compact without hiding labels", () => {
    expect(css).toContain(".global-nav__link:any-link { min-height: 48px");
    expect(css).toContain(".check-grid { grid-template-columns: repeat(2, minmax(0, 1fr))");
    expect(css).toContain(".form-actions .button { width: 100%; }");
  });
});
