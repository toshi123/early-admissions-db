import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const css = readFileSync(join(process.cwd(), "src/styles.css"), "utf8");
const main = readFileSync(join(process.cwd(), "src/main.ts"), "utf8");

function luminance(hex: string): number {
  const channels = hex.match(/[a-f\d]{2}/gi)!.map((value) => {
    const channel = Number.parseInt(value, 16) / 255;
    return channel <= .04045 ? channel / 12.92 : ((channel + .055) / 1.055) ** 2.4;
  });
  return channels[0] * .2126 + channels[1] * .7152 + channels[2] * .0722;
}

function contrast(a: string, b: string): number {
  const [lighter, darker] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (lighter + .05) / (darker + .05);
}

describe("DADS component contracts", () => {
  it("meets text and non-text contrast targets for the adopted key colors", () => {
    expect(contrast("#333333", "#ffffff")).toBeGreaterThanOrEqual(4.5);
    expect(contrast("#00118f", "#ffffff")).toBeGreaterThanOrEqual(4.5);
    expect(contrast("#949494", "#ffffff")).toBeGreaterThanOrEqual(3);
  });

  it("uses full clickable labels and native checkbox/radio inputs", () => {
    const label = document.createElement("label");
    label.className = "choice choice--checkbox";
    label.innerHTML = '<span class="choice__control"><input type="checkbox"></span><span class="choice__label">工学</span>';
    document.body.append(label);
    const checkbox = label.querySelector<HTMLInputElement>("input")!;
    label.click();
    expect(checkbox.checked).toBe(true);

    label.className = "choice choice--radio";
    label.innerHTML = '<span class="choice__control"><input type="radio" name="answer"></span><span class="choice__label">指定なし</span>';
    const radio = label.querySelector<HTMLInputElement>("input")!;
    label.click();
    expect(radio.checked).toBe(true);
    expect(css).toContain(".choice input:focus-visible");
  });

  it("links the global navigation to the usage guide", () => {
    expect(main).toContain('href="/guide" data-route');
    expect(main).toContain('>使い方</a>');
    expect(main).toContain('if (path === "/guide")');
  });

  it("keeps formal desktop labels and accessible names beside mobile short labels", () => {
    expect(main).toContain('<span class="nav-label--desktop">候補リスト</span>');
    expect(main).toContain('<span class="nav-label--mobile" aria-hidden="true">候補</span>');
    expect(main).toContain('aria-label="候補リスト（${candidates.store.items.length}件）"');
    expect(main).toContain('<span class="nav-label--desktop">データについて</span>');
    expect(main).toContain('<span class="nav-label--mobile" aria-hidden="true">データ</span>');
    expect(main).toContain('aria-label="データについて"');
  });

  it("uses a native grade requirement checkbox with a dependent disabled input", () => {
    expect(main).toContain('id="grade-requirement" type="checkbox"');
    expect(main).toContain('id="overall-gpa"');
    expect(main).toContain('applied.grade_requirement_status === "required" ? "" : "disabled"');
    expect(main).toContain("評定を出願条件として求める入試を検索します");
    expect(main).toContain("全体評定について安全に数値判定できるものだけを絞り込みます");
  });

  it("keeps the university field an exact-selection ARIA combobox", () => {
    expect(main).toContain('role="combobox"');
    expect(main).toContain('aria-autocomplete="list"');
    expect(main).toContain('aria-controls="university-suggestions"');
    expect(main).toContain('role="option"');
  });

  it("uses native disclosure semantics and a stable content label", () => {
    expect(main).toContain('<details id="prefecture-details" class="disclosure">');
    expect(main).toContain("10. 都道府県で絞り込む");
    expect(css).toContain(".disclosure summary:focus-visible");
  });

  it("gives buttons DADS focus treatment and practical target sizing", () => {
    expect(main).toContain('class="button button--primary"');
    expect(main).toContain('class="button button--outline"');
    expect(css).toContain(".button { min-height: 48px");
    expect(css).toContain("outline: 4px solid #000");
  });

  it("uses a labelled page-navigation pattern and hides unavailable directions", () => {
    expect(main).toContain('aria-label="検索結果のページ"');
    expect(main).toContain("前のページ");
    expect(main).toContain("次のページ");
    expect(main).toContain('class="pagination__spacer" aria-hidden="true"');
    expect(main).not.toContain('applied.page <= 1 ? "disabled"');
  });

  it("uses button-based DADS disclosures for university result groups", () => {
    expect(main).toContain('button[data-university-toggle]');
    expect(main).toContain('setAttribute("aria-expanded", String(expanded))');
    expect(css).toContain(".university-disclosure__button:focus-visible");
    expect(css).toContain('.university-disclosure__button[aria-expanded="true"] .university-disclosure__icon');
  });

  it("keeps the detail heading concise without redundant return or general eligibility notices", () => {
    expect(main).not.toContain("← 検索結果へ戻る");
    expect(main).not.toContain("このページは出願資格や合格可能性を判定しません");
    expect(main).toContain('<header class="detail-title">');
    expect(main).toContain('class="fallback-warning"');
  });

  it("uses labelled floating navigation with native actions and no summary-level return link", () => {
    expect(main).toContain('aria-label="検索結果の操作"');
    expect(main).toContain('aria-label="入試詳細の操作"');
    expect(main).toContain('data-detail-history-back');
    expect(main).toContain('history.back()');
    expect(main).toContain('data-start-at-top');
    expect(main).not.toContain('data-route>検索条件を変更</a></section>');
    expect(css).toContain('.floating-navigation__action:any-link');
    expect(css).toContain(':focus-visible');
  });

  it("places raw dates before selection and eligibility without moving the fallback warning", () => {
    const sectionSource = main.slice(main.indexOf("const sections:"), main.indexOf("const labels:"));
    const headings = [...sectionSource.matchAll(/\["(基本情報|日程|選考方法|出願条件|研究)"/g)].map((match) => match[1]);
    expect(headings).toEqual(["基本情報", "日程", "選考方法", "出願条件", "研究"]);
    expect(main).toContain('class="fallback-warning"');
    expect(main.indexOf('<h2>その他の記録項目</h2>')).toBeLessThan(main.indexOf('<h2>出典</h2>'));
  });
});
