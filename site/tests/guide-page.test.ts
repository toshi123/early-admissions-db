import { describe, expect, it } from "vitest";
import { guidePage } from "../src/guide-page";

describe("usage guide", () => {
  it("keeps the requested section order and working in-page navigation", () => {
    document.body.innerHTML = guidePage();
    const ids = [...document.querySelectorAll<HTMLElement>(".guide-section")]
      .map((section) => section.id);
    expect(ids).toEqual([
      "guide-university",
      "guide-academic-field",
      "guide-requirements",
      "guide-grade",
      "guide-prefecture",
      "guide-save-download",
    ]);
    const targets = [...document.querySelectorAll<HTMLAnchorElement>(".guide-toc a")]
      .map((link) => link.hash.slice(1));
    expect(targets).toEqual(ids);
    for (const target of targets) expect(document.getElementById(target)).not.toBeNull();
  });

  it("uses all captured guide images with meaningful alternative text", () => {
    document.body.innerHTML = guidePage();
    const images = [...document.querySelectorAll<HTMLImageElement>(".guide-figure img")];
    expect(images.map((image) => image.getAttribute("src"))).toEqual([
      "/guide/university-search-nagoya.png",
      "/guide/academic-field-selection.png",
      "/guide/research-and-test-filters.png",
      "/guide/search-results-sail.png",
      "/guide/grade-and-prefecture-filters.png",
      "/guide/save-nagoya.png",
      "/guide/save-kitasato.png",
      "/guide/saved-admissions.png",
      "/guide/excel-download.png",
    ]);
    expect(images.every((image) => (image.alt?.length ?? 0) >= 15)).toBe(true);
    expect(images.every((image) => !/画像\d|スクリーンショット/.test(image.alt))).toBe(true);
  });

  it("documents current matching, persistence, and export boundaries", () => {
    const html = guidePage();
    expect(html).toContain("文字を入力しただけでは検索できません");
    expect(html).toContain("異なる項目はAND");
    expect(html).toContain("いずれかに一致（OR）");
    expect(html).toContain("「不明」や未記録の入試は含みません");
    expect(html).toContain("別の端末には同期されません");
    expect(html).toContain("選択中の候補だけ");
    expect(html).toContain("early-admissions-candidates-YYYY-MM-DD.csv");
    expect(html).toContain("Excelのシート名は「候補リスト」");
  });

  it("links to reproducible Nagoya and academic-field examples", () => {
    document.body.innerHTML = guidePage();
    const routeLinks = [...document.querySelectorAll<HTMLAnchorElement>("a[data-route]")]
      .map((link) => link.getAttribute("href"));
    expect(routeLinks).toContain("/search?university=%E5%90%8D%E5%8F%A4%E5%B1%8B%E5%A4%A7%E5%AD%A6");
    expect(routeLinks.some((href) => href?.includes("academic_field_v2=natural_sciences"))).toBe(true);
    expect(routeLinks.some((href) => href?.includes("research_requirement_required=Yes"))).toBe(true);
  });
});
