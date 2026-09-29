import { escapeHtml } from "./display";
import { compactResultCard } from "./search-ui";
import type { ProvisionalAdmission, SearchRequest, SearchRow } from "./types";
import { hasUnverifiedFilters, provisionalCard } from "./public-discovery";

export const UNIVERSITY_GROUP_PAGE_SIZE = 15;

export interface UniversityAdmissionGroup {
  university: string;
  admissions: SearchRow[];
}

export interface PublicUniversityGroup extends UniversityAdmissionGroup {
  provisional: ProvisionalAdmission[];
}

export function groupPublicAdmissionsByUniversity(rows: SearchRow[], provisional: ProvisionalAdmission[]): PublicUniversityGroup[] {
  const groups = groupAdmissionsByUniversity(rows).map((group) => ({ ...group, provisional: [] as ProvisionalAdmission[] }));
  const byUniversity = new Map(groups.map((group) => [group.university, group]));
  for (const record of provisional) {
    let group = byUniversity.get(record.university);
    if (!group) {
      group = { university: record.university, admissions: [], provisional: [] };
      groups.push(group);
      byUniversity.set(record.university, group);
    }
    group.provisional.push(record);
  }
  return groups;
}

export function publicUniversityGroupMarkup(group: PublicUniversityGroup, globalIndex: number,
  expanded: boolean, request: SearchRequest): string {
  const content = [
    ...group.admissions.map((row) => compactResultCard(row, request.gpa_tenths !== null, false)),
    ...group.provisional.map((record) => provisionalCard(record, hasUnverifiedFilters(request), request)),
  ].join("");
  return universityDisclosureMarkup(group.university, group.admissions.length + group.provisional.length,
    globalIndex, expanded, content);
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

export function paginateUniversityGroups<T extends UniversityAdmissionGroup>(
  groups: T[],
  page: number,
  pageSize = UNIVERSITY_GROUP_PAGE_SIZE,
): T[] {
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
  return universityDisclosureMarkup(group.university, group.admissions.length, globalIndex, expanded,
    group.admissions.map((row) => compactResultCard(row, showGpaSafeMatch, false)).join(""));
}

export function universityDisclosureMarkup(
  name: string, count: number, globalIndex: number, expanded: boolean, content: string,
): string {
  const buttonId = `university-toggle-${globalIndex}`;
  const panelId = `university-panel-${globalIndex}`;
  const university = escapeHtml(name);
  return `<section class="university-group" role="listitem">
    <h2 class="university-group__heading"><button id="${buttonId}" class="university-disclosure__button" type="button" data-university-toggle="${university}" aria-expanded="${expanded}" aria-controls="${panelId}">
      <svg class="university-disclosure__icon" width="24" height="24" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="11" fill="currentcolor"/><circle class="university-disclosure__icon-circle" cx="12" cy="12" r="8" fill="currentcolor"/><path d="M17 10H7L12 15L17 10Z" fill="Canvas"/></svg>
      <span class="university-disclosure__name">${university}</span><span class="university-disclosure__count">${count.toLocaleString("ja-JP")}件</span>
    </button></h2>
    <div id="${panelId}" class="university-admissions" role="region" aria-labelledby="${buttonId}"${expanded ? "" : " hidden"}>
      <div class="university-admissions__list" role="list">${content}</div>
    </div>
  </section>`;
}
