import type { DetailRecord, SearchRow } from "../src/types";
export const candidateRow = (update: Partial<SearchRow> = {}): SearchRow => ({
  source_dataset: "kokkoritsu", source_version: "5.61", record_id: "A/1", university: "東京大学",
  faculty_school: "工学部", department: "情報学科", selection_category: "総合型選抜", selection_name: "特別選抜",
  institution_type: "国立", prefecture: "東京都", application_end: " 11月6日（必着）\n午後5時 ",
  gpa_requirement: "3.8以上", english_requirement: "英検2級以上", english_requirement_status: "required",
  research_requirement_required: "Yes", selection_interview: "Yes", selection_essay: "Yes",
  selection_oral_exam: "Unknown", fallback_previous_year: false, detail_path: "details.json", ...update,
} as SearchRow);
export const candidateDetail = (row = candidateRow()): DetailRecord => ({
  identity: { source_dataset: row.source_dataset, source_version: row.source_version, record_id: row.record_id },
  admission: { ...row, source_url: "https://example.test/info?q=1&lang=ja", research_requirement_summary: '研究発表, "受賞"\n証明書を提出' },
  research_requirements: [],
} as unknown as DetailRecord);
