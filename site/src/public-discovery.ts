import { escapeHtml, safeExternalLink } from "./display";
import type { ProvisionalAdmission, SearchRequest, SearchRow } from "./types";

export function discoverProvisional(records: ProvisionalAdmission[], request: SearchRequest, confirmed: SearchRow[] = []): ProvisionalAdmission[] {
  // Only verified identity fields can exclude a provisional record. Other
  // filters have unknown truth values and must not imply Yes or No.
  return records.filter((record) =>
    !confirmed.some((row) => row.university === record.university && row.selection_name === record.selection_name &&
      (!record.faculty_school || row.faculty_school === record.faculty_school)) &&
    (!request.university.length || request.university.includes(record.university)) &&
    (!request.institution_type.length || request.institution_type.includes(record.institution_type)) &&
    (request.special_filters.length
      ? request.special_filters.some((filter) => ({
        returnee_flag: "returnee", international_baccalaureate_flag: "international_baccalaureate",
        private_foreign_student_flag: "private_foreign_student", adult_selection_flag: "adult",
      })[filter] === record.special_filter_tag ||
        (filter === "private_foreign_student_flag" && record.special_filter_tag === "unclassified_international"))
      : (record.special_filter_tag === "none" && request.selection_families.includes(record.selection_family as "recommendation" | "comprehensive")) ||
        record.special_filter_tag === "unclassified_international"));
}

export function hasUnverifiedFilters(request: SearchRequest): boolean {
  return request.prefecture.length > 0 || request.prefecture_membership.length > 0 ||
    request.academic_field.length > 0 || request.academic_field_group.length > 0 ||
    request.academic_field_mapping_status.length > 0 || request.academic_field_v2_branches.length > 0 ||
    request.stem_flag !== null || request.selection_category.length > 0 ||
    request.exclusive_enrollment_status.length > 0 || request.school_recommendation_required.length > 0 ||
    request.academic_record_required.length > 0 || request.common_test_required.length > 0 ||
    request.research_requirement_required.length > 0 || request.research_activity_level_status.length > 0 ||
    request.selection_interview.length > 0 || request.selection_oral_exam.length > 0 ||
    request.selection_presentation.length > 0 || request.selection_essay.length > 0 ||
    request.selection_written_exam.length > 0 || request.selection_common_test.length > 0 ||
    request.english_requirement_status.length > 0 || request.gpa_tenths !== null ||
    request.grade_requirement_status !== null || request.overall_gpa_tenths !== null ||
    request.applicant_gpa_tenths !== null || request.deadline_on_or_after !== null;
}

export function provisionalCountLabel(records: ProvisionalAdmission[]): string {
  return records.every((record) => record.public_status === "details_pending")
    ? "詳細確認中" : "詳細確認中・公表待ち等";
}

export function provisionalCard(record: ProvisionalAdmission, filtersUnverified: boolean, request?: SearchRequest): string {
  const status = record.public_status === "details_pending"
    ? "2027年度実施確認済み・詳細確認中"
    : record.public_status === "previous_year_reference"
      ? "2027年度実施確認済み・前年資料を参考表示"
      : "2027年度実施予定・募集要項公開待ち";
  const previousYear = record.previous_year_source_url
    ? `<p class="fallback-warning">前年実績（2026年度）であり、2027年度は変更される可能性があります。${record.previous_year_detail ? ` ${escapeHtml(record.previous_year_detail)}` : ""}</p>${safeExternalLink(record.previous_year_source_url, "2026年度公式資料")}`
    : "";
  const release = record.release_expected_text
    ? `<p>募集要項の公開予定：${escapeHtml(record.release_expected_text)}</p>` : "";
  return `<article class="result-card provisional-card" role="listitem" data-public-status="${record.public_status}">
    <h3>${escapeHtml(record.university)}</h3><p class="faculty-line">${escapeHtml(record.faculty_school ?? "学部等未確定")}</p>
    <p class="selection-line"><strong>${escapeHtml(record.selection_name)}</strong></p>
    <p class="provisional-status"><strong>${status}</strong></p>
    ${record.special_filter_tag === "unclassified_international" && request?.special_filters.includes("private_foreign_student_flag") ? '<p class="filter-unknown">「私費外国人留学生」に該当するか未確認です。留学生一般としての実施のみ確認しています。</p>' : ""}
    ${filtersUnverified ? '<p class="help">指定された詳細条件への適合は未判定です。</p>' : ""}
    ${request?.deadline_on_or_after ? '<p class="filter-unknown">出願締切を確認できていません。大学公式資料をご確認ください。</p>' : ""}
    ${request?.applicant_gpa_tenths !== null && request?.applicant_gpa_tenths !== undefined ? '<p class="filter-unknown">評定条件を数値だけで判定できません。大学公式資料をご確認ください。</p>' : ""}
    <p>${escapeHtml(record.known_scope)}</p><p>${escapeHtml(record.known_detail)}</p><p>未確定：${escapeHtml(record.unknown_detail)}</p>${release}
    <p class="help">詳細は大学公式資料を必ず確認してください。</p>
    <div class="source-links">${safeExternalLink(record.official_source_url, "2027年度大学公式情報")}${previousYear}</div>
  </article>`;
}
