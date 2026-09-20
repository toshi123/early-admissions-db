import { escapeHtml } from "./display";
import { compactResultCard } from "./search-ui";
import type { SearchRow } from "./types";

export const UNIVERSITY_GROUP_PAGE_SIZE = 15;

export interface UniversityAdmissionGroup {
  university: string;
  admissions: SearchRow[];
}

export function admissionLogicalKey(row: SearchRow): string {
  return `${row.source_dataset}\u0000${row.source_version}\u0000${row.record_id}`;
}

export function groupAdmissionsByUniversity(rows: SearchRow[]): UniversityAdmissionGroup[] {
  const groups: UniversityAdmissionGroup[] = [];
  const byUniversity = new Map<string, UniversityAdmissionGroup>();
  for (const row of rows) {
    let group = byUniversity.get(row.university);
    if (!group) {
      group = { university: row.university, admissions: [] };
      byUniversity.set(row.university, group);
      groups.push(group);
    }
    group.admissions.push(row);
  }
  return groups;
}

export function paginateUniversityGroups(
  groups: UniversityAdmissionGroup[],
  page: number,
  pageSize = UNIVERSITY_GROUP_PAGE_SIZE,
): UniversityAdmissionGroup[] {
  const start = (Math.max(1, page) - 1) * pageSize;
  return groups.slice(start, start + pageSize);
}

export function expandedUniversitiesFromHistory(state: unknown): Set<string> {
  if (!state || typeof state !== "object") return new Set();
  const values = (state as { expandedUniversities?: unknown }).expandedUniversities;
  if (!Array.isArray(values)) return new Set();
  return new Set(values.filter((value): value is string => typeof value === "string"));
}

export function universityResultsHistoryState(
  state: unknown,
  expanded: Set<string>,
  scrollY: number,
  prefectureOpen: boolean,
): Record<string, unknown> {
  const existing = state && typeof state === "object" ? state as Record<string, unknown> : {};
  return {
    ...existing,
    scrollY,
    prefectureOpen,
    expandedUniversities: [...expanded],
  };
}

export function toggleExpandedUniversity(expanded: Set<string>, university: string): boolean {
  if (expanded.has(university)) {
    expanded.delete(university);
    return false;
  }
  expanded.add(university);
  return true;
}

export function universityGroupMarkup(
  group: UniversityAdmissionGroup,
  globalIndex: number,
  expanded: boolean,
  showGpaSafeMatch: boolean,
): string {
  const buttonId = `university-toggle-${globalIndex}`;
  const panelId = `university-panel-${globalIndex}`;
  const university = escapeHtml(group.university);
  return `<section class="university-group" role="listitem">
    <h2 class="university-group__heading"><button id="${buttonId}" class="university-disclosure__button" type="button" data-university-toggle="${university}" aria-expanded="${expanded}" aria-controls="${panelId}">
      <svg class="university-disclosure__icon" width="24" height="24" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="11" fill="currentcolor"/><circle class="university-disclosure__icon-circle" cx="12" cy="12" r="8" fill="currentcolor"/><path d="M17 10H7L12 15L17 10Z" fill="Canvas"/></svg>
      <span class="university-disclosure__name">${university}</span><span class="university-disclosure__count">${group.admissions.length.toLocaleString("ja-JP")}件</span>
    </button></h2>
    <div id="${panelId}" class="university-admissions" role="region" aria-labelledby="${buttonId}"${expanded ? "" : " hidden"}>
      <div class="university-admissions__list" role="list">${group.admissions.map((row) => compactResultCard(row, showGpaSafeMatch, false)).join("")}</div>
    </div>
  </section>`;
}
