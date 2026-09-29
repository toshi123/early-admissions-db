import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const css = readFileSync(join(process.cwd(), "src/styles.css"), "utf8");

describe("responsive search and compact results contract", () => {
  it("does not force overflow when a 320px viewport reserves a scrollbar gutter", () => {
    expect(css).toContain("min-width: min(320px, 100%)");
    expect(css).not.toContain("min-width: 320px;");
  });
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
    expect(css).toContain(".global-nav__link:any-link { min-width: 0; width: 100%; min-height: 48px");
    expect(css).toContain(".global-nav { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); }");
    expect(css).toContain(".global-nav li { min-width: 0; }");
    expect(css).toContain("width: 100%; min-height: 48px; padding: .75rem .25rem; justify-content: center");
    expect(css).toContain(".nav-label--desktop { display: none; }");
    expect(css).toContain(".nav-label--mobile { display: inline; }");
    expect(css).toContain(".check-grid { grid-template-columns: repeat(2, minmax(0, 1fr))");
    expect(css).toContain(".form-actions .button { width: 100%; }");
  });

  it("keeps the actual search submit in a safe-area mobile bottom bar", () => {
    const mobileCss = css.slice(css.indexOf("@media (max-width: 620px) {"));
    expect(mobileCss).toContain(".search-page { padding-bottom: calc(6rem + env(safe-area-inset-bottom)); }");
    expect(mobileCss).toContain(".search-page + footer { padding-bottom: calc(6rem + env(safe-area-inset-bottom)); }");
    expect(mobileCss).toContain(".submit-action {\n    position: fixed;");
    expect(mobileCss).toContain("inset: auto 0 0;");
    expect(mobileCss).toContain("padding: .625rem .75rem calc(.625rem + env(safe-area-inset-bottom));");
    expect(mobileCss).toContain("background: #fff;");
  });

  it("keeps guide images and its table of contents within the mobile viewport", () => {
    expect(css).toContain(".guide-figure img { display: block; width: 100%; height: auto; }");
    expect(css).toContain(".guide-image-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr))");
    expect(css).toContain(".guide-toc ol { columns: 1; }");
    expect(css).toContain(".guide-image-grid { grid-template-columns: 1fr; }");
  });

  it("keeps Broad groups responsive and their dynamic children visibly nested", () => {
    expect(css).toContain(".academic-field-branch-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr))");
    expect(css).toContain(".academic-subcategory-filter {");
    expect(css).toContain("border-left: 3px solid var(--gray-300)");
    expect(css).toContain(".academic-subcategory-filter[hidden] { display: none; }");
    expect(css).toContain(".academic-field-branch-grid { grid-template-columns: 1fr; }");
  });

  it("keeps university disclosures and nested admissions compact on mobile", () => {
    expect(css).toContain(".university-disclosure__button { min-height: 52px");
    expect(css).toContain(".university-disclosure__name { font-size: 1rem; }");
    expect(css).toContain(".university-admissions { margin: 0 .25rem .75rem 1rem; }");
  });

  it("keeps all result-chip categories in one wrapping row beside the candidate action", () => {
    expect(css).toContain(".result-card__utility { display: flex;");
    expect(css).toContain(".result-chips { min-width: 0; display: flex; flex: 1 1 auto; flex-wrap: wrap;");
    expect(css).toContain(".method-chip {");
    expect(css).toContain(".condition-chip {");
    expect(css).toContain(".exclusive-chip {");
    expect(css).toContain(".result-card__utility { flex-wrap: wrap; }");
  });

  it("keeps the dependent overall-grade control within the mobile viewport", () => {
    expect(css).toContain(".nested-filter { margin: 1rem 0 0 2.5rem;");
    expect(css).toContain(".grade-input-row { display: flex;");
    expect(css).toContain("@media (max-width: 40rem) { .nested-filter { margin-left: 0; } }");
  });

  it("anchors the desktop navigation to the content edge and uses one borderless action surface", () => {
    expect(css).toContain(".floating-navigation {");
    expect(css).toContain("position: fixed;");
    expect(css).toContain("top: 5rem");
    expect(css).toContain("left: calc(50% + var(--floating-content-half) + 1rem)");
    expect(css).toContain(".floating-navigation--results { --floating-content-half: 390px; }");
    expect(css).toContain("--floating-content-half: 430px");
    expect(css).toContain("border: 0;");
    expect(css).toContain("border-radius: 0;");
    expect(css).toContain("background: transparent;");
    expect(css).toContain("min-height: 44px;");
    expect(css).toContain("font-size: 1rem;");
    expect(css).toContain("border-top: 1px solid var(--gray-200)");
    expect(css).toContain(".floating-navigation .candidate-toggle:hover { background: var(--blue-50); }");
  });

  it("falls back to a safe-area action bar when the side rail does not fit", () => {
    expect(css).toContain("@media (max-width: 1260px)");
    expect(css).toContain("padding-bottom: calc(6rem + env(safe-area-inset-bottom))");
    expect(css).toContain("padding: .625rem .75rem calc(.625rem + env(safe-area-inset-bottom))");
    expect(css).toContain("inset: auto 0 0");
    expect(css).toContain("border-left: 1px solid var(--gray-200)");
  });
});
