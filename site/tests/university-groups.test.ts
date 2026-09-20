import { describe, expect, it } from "vitest";
import type { SearchRow } from "../src/types";
import {
  admissionLogicalKey,
  expandedUniversitiesFromHistory,
  groupAdmissionsByUniversity,
  paginateUniversityGroups,
  toggleExpandedUniversity,
  UNIVERSITY_GROUP_PAGE_SIZE,
  universityGroupMarkup,
  universityResultsHistoryState,
} from "../src/university-groups";

function row(university: string, recordId: string): SearchRow {
  return {
    source_dataset: "fixture",
    source_version: "1",
    record_id: recordId,
    university,
    faculty_school: "工学部",
    department: "情報工学科",
    selection_category: "総合型選抜",
    selection_name: `選抜 ${recordId}`,
    selection_interview: "Yes",
    selection_oral_exam: "No",
    selection_presentation: "No",
    selection_essay: "No",
    selection_written_exam: "No",
    selection_practical: "No",
    selection_group_discussion: "No",
    selection_aptitude_test: "No",
    selection_common_test: "No",
    fallback_previous_year: false,
  } as SearchRow;
}

describe("university result grouping", () => {
  it("uses first-appearance university order and preserves admission order within each group", () => {
    const rows = [
      row("東京大学", "A"),
      row("中央大学", "B"),
      row("東京大学", "C"),
      row("中央大学", "D"),
    ];
    const groups = groupAdmissionsByUniversity(rows);
    expect(groups.map((group) => group.university)).toEqual(["東京大学", "中央大学"]);
    expect(groups[0].admissions.map((item) => item.record_id)).toEqual(["A", "C"]);
    expect(groups[1].admissions.map((item) => item.record_id)).toEqual(["B", "D"]);
  });

  it("preserves the complete logical result set and summary cardinalities", () => {
    const rows = [row("東京大学", "A"), row("中央大学", "B"), row("東京大学", "C")];
    const groups = groupAdmissionsByUniversity(rows);
    const groupedRows = groups.flatMap((group) => group.admissions);
    expect(groups.reduce((total, group) => total + group.admissions.length, 0)).toBe(rows.length);
    expect(groups.length).toBe(new Set(rows.map((item) => item.university)).size);
    expect(new Set(groupedRows.map(admissionLogicalKey))).toEqual(new Set(rows.map(admissionLogicalKey)));
  });

  it("paginates whole university groups without splitting their admissions", () => {
    const rows = Array.from({ length: 18 }, (_, index) => row("大学A", `A-${index}`));
    for (let index = 0; index < 30; index += 1) rows.push(row(`大学${index + 1}`, `B-${index}`));
    const groups = groupAdmissionsByUniversity(rows);
    const firstPage = paginateUniversityGroups(groups, 1);
    const secondPage = paginateUniversityGroups(groups, 2);
    expect(UNIVERSITY_GROUP_PAGE_SIZE).toBe(15);
    expect(firstPage).toHaveLength(15);
    expect(firstPage[0].admissions).toHaveLength(18);
    expect(secondPage.some((group) => group.university === "大学A")).toBe(false);
  });

  it("renders every university collapsed by default with an accessible button and count", () => {
    document.body.innerHTML = universityGroupMarkup(
      { university: "東京大学", admissions: [row("東京大学", "A"), row("東京大学", "B")] },
      0,
      false,
      false,
    );
    const button = document.querySelector<HTMLButtonElement>("button[data-university-toggle]")!;
    const panel = document.getElementById(button.getAttribute("aria-controls")!)!;
    expect(button.type).toBe("button");
    expect(button.getAttribute("aria-expanded")).toBe("false");
    expect(panel.hidden).toBe(true);
    expect(button.textContent).toContain("東京大学");
    expect(button.textContent).toContain("2件");
    expect(panel.querySelectorAll("article.result-card")).toHaveLength(2);
    expect(panel.textContent).not.toContain("東京大学");
  });

  it("renders an expanded group with matching aria state and visible admission panel", () => {
    document.body.innerHTML = universityGroupMarkup(
      { university: "中央大学", admissions: [row("中央大学", "A")] },
      4,
      true,
      false,
    );
    const button = document.querySelector<HTMLButtonElement>("button")!;
    const panel = document.getElementById(button.getAttribute("aria-controls")!)!;
    expect(button.getAttribute("aria-expanded")).toBe("true");
    expect(panel.hidden).toBe(false);
    expect(panel.getAttribute("aria-labelledby")).toBe(button.id);
  });

  it("allows multiple universities to remain expanded and toggles independently", () => {
    const expanded = new Set<string>();
    expect(toggleExpandedUniversity(expanded, "大学A")).toBe(true);
    expect(toggleExpandedUniversity(expanded, "大学B")).toBe(true);
    expect([...expanded]).toEqual(["大学A", "大学B"]);
    expect(toggleExpandedUniversity(expanded, "大学A")).toBe(false);
    expect([...expanded]).toEqual(["大学B"]);
  });

  it("restores history-scoped expansion but starts a new search collapsed", () => {
    expect([...expandedUniversitiesFromHistory({ expandedUniversities: ["大学A", "大学B"] })]).toEqual(["大学A", "大学B"]);
    expect([...expandedUniversitiesFromHistory({ transition: "search-submit" })]).toEqual([]);
    expect([...expandedUniversitiesFromHistory(null)]).toEqual([]);
  });

  it("preserves scroll and expanded groups together for detail-to-back restoration", () => {
    const state = universityResultsHistoryState(
      { from: "/search?institution_type=国立" },
      new Set(["大学A", "大学B"]),
      1240,
      true,
    );
    expect(state).toEqual({
      from: "/search?institution_type=国立",
      scrollY: 1240,
      prefectureOpen: true,
      expandedUniversities: ["大学A", "大学B"],
    });
    expect([...expandedUniversitiesFromHistory(state)]).toEqual(["大学A", "大学B"]);
  });
});
