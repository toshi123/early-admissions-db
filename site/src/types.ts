export type Nullable<T> = T | null;
export type Scalar = string | number | boolean | null;

export interface ArtifactReceipt {
  kind: "search_shard" | "detail_shard" | "filter_options";
  path: string;
  sha256: string;
  size_bytes: number;
  record_count: number;
}

export interface SiteManifest {
  artifact: string;
  manifest_version: string;
  site_data_schema_version: "0.2";
  build_id: string;
  build_timestamp_utc: string;
  builder_version: string;
  input: {
    sqlite_sha256: string;
    sqlite_schema_version: string;
    unified_contract_version: string;
    source_versions: Record<string, string>;
    gpa_parser_contract_version: string;
    grade_requirement_mapping_contract_version: string;
    grade_requirement_crosswalk_sha256: string;
    academic_field_mapping_contract_version: string;
    academic_field_taxonomy_version: string;
    academic_field_v2_mapping_contract_version: string;
    academic_field_v2_taxonomy_version: string;
    english_requirement_parser_contract_version: string;
    prefecture_mapping_contract_version: string;
    prefecture_taxonomy_version: string;
  };
  grade_requirement_search: {
    mapping_contract_version: string;
    crosswalk_distinct_non_null_raw_values: number;
    audited_distinct_raw_classes: number;
    classification_counts: Record<string, number>;
    overall_status_counts: Record<string, number>;
    numeric_floor_rows: number;
    raw_mismatch_rows: number;
    representative_review_record_ids: string[];
    representative_unmapped_record_ids: string[];
  };
  outputs: { artifacts: ArtifactReceipt[] };
  counts: {
    search_rows: number;
    detail_records: number;
    research_requirement_rows: number;
    universities: number;
    fallback_rows: number;
    source_datasets: Record<string, number>;
  };
  validation: { status: "passed" } & Record<string, string>;
}

export interface SearchRow {
  source_dataset: string;
  source_version: string;
  record_id: string;
  institution_type: string;
  university: string;
  prefecture: Nullable<string>;
  prefecture_raw: Nullable<string>;
  prefecture_mapping_status: string;
  prefecture_memberships: string[];
  faculty_school: Nullable<string>;
  department: Nullable<string>;
  selection_category: Nullable<string>;
  selection_name: Nullable<string>;
  slot_type: Nullable<string>;
  capacity: Nullable<string>;
  academic_field: Nullable<string>;
  stem_flag: Nullable<boolean>;
  academic_field_mapping_status: string;
  academic_field_groups: string[];
  academic_field_v2_broad_mapping_status: string;
  academic_field_v2_subcategory_mapping_status: string;
  academic_field_v2_broad_memberships: string[];
  academic_field_v2_subcategory_memberships: string[];
  academic_field_v2_mapping_contract_version: "0.2";
  academic_field_v2_taxonomy_version: "0.2";
  exclusive_enrollment_status: Nullable<string>;
  school_recommendation_required: Nullable<string>;
  academic_record_required: Nullable<string>;
  common_test_required: Nullable<string>;
  research_requirement_required: Nullable<string>;
  research_activity_level_status: Nullable<string>;
  selection_interview: Nullable<string>;
  selection_oral_exam: Nullable<string>;
  selection_presentation: Nullable<string>;
  selection_essay: Nullable<string>;
  selection_written_exam: Nullable<string>;
  selection_practical: Nullable<string>;
  selection_group_discussion: Nullable<string>;
  selection_aptitude_test: Nullable<string>;
  selection_common_test: Nullable<string>;
  gpa_requirement: Nullable<string>;
  english_requirement: Nullable<string>;
  english_requirement_status: "required" | "not_required" | "review_required" | "unknown" | "not_applicable" | "unmapped";
  english_requirement_parse_status: "exact_crosswalk" | "missing" | "unmapped";
  english_requirement_search_disposition: "safe_exact" | "review_required" | "not_searchable";
  gpa_parse_status: string;
  gpa_search_disposition: string;
  gpa_min_tenths: Nullable<number>;
  gpa_min_inclusive: Nullable<boolean>;
  gpa_max_tenths: Nullable<number>;
  gpa_max_inclusive: Nullable<boolean>;
  gpa_source_value_status: string;
  grade_requirement_status: "required" | "not_required" | "review_required" | "unknown" | "not_applicable" | "unmapped";
  overall_gpa_min_tenths: Nullable<number>;
  overall_gpa_min_inclusive: Nullable<boolean>;
  overall_gpa_status: string;
  additional_grade_conditions: Nullable<boolean>;
  application_start: Nullable<string>;
  application_end: Nullable<string>;
  fallback_previous_year: Nullable<boolean>;
  information_year: Nullable<number>;
  publication_status: Nullable<string>;
  detail_path: string;
  gpa_derived_status?: GpaDerivedStatus;
}

export interface OptionValue {
  value: Nullable<string>;
  display_label: string;
  unfiltered_count: number;
}

export interface AcademicGroupOption extends OptionValue {
  value: string;
  description: string;
  display_order: number;
}
export interface PrefectureOption extends OptionValue { value:string; region:string; display_order:number; }

export interface AcademicFieldV2BroadOption {
  group_code: string;
  display_label_ja: string;
  ui_section: string;
  display_order: number;
  unfiltered_count: number;
}

export interface AcademicFieldV2SubcategoryOption {
  subcategory_code: string;
  display_label_ja: string;
  parent_group_code: string;
  display_order: number;
  ui_status: "primary" | "secondary" | "hidden";
  unfiltered_count: number;
}

export interface FilterOptions {
  site_data_schema_version: "0.2";
  build_id: string;
  universities: OptionValue[];
  institution_types: OptionValue[];
  prefectures: OptionValue[];
  academic_field_groups: AcademicGroupOption[];
  academic_field_v2_broad_groups: AcademicFieldV2BroadOption[];
  academic_field_v2_subcategories: AcademicFieldV2SubcategoryOption[];
  raw_academic_fields: OptionValue[];
  academic_field_mapping_statuses: OptionValue[];
  selection_categories: OptionValue[];
  exclusive_enrollment_statuses: OptionValue[];
  school_recommendation_required: OptionValue[];
  academic_record_required: OptionValue[];
  common_test_required: OptionValue[];
  research_requirement_required: OptionValue[];
  research_activity_level_status: OptionValue[];
  english_requirement_statuses: OptionValue[];
  prefecture_memberships: PrefectureOption[];
  selection_method_values: Record<string, OptionValue[]>;
}

export type MultiField =
  | "university" | "institution_type" | "prefecture" | "academic_field"
  | "academic_field_group" | "academic_field_mapping_status" | "selection_category"
  | "exclusive_enrollment_status" | "school_recommendation_required"
  | "academic_record_required" | "common_test_required" | "research_requirement_required"
  | "research_activity_level_status" | "selection_interview" | "selection_oral_exam"
  | "selection_presentation" | "selection_essay" | "selection_written_exam"
  | "selection_common_test" | "english_requirement_status" | "prefecture_membership";

export interface SearchRequest {
  university: string[];
  institution_type: string[];
  prefecture: string[];
  prefecture_membership: string[];
  academic_field: string[];
  academic_field_group: string[];
  academic_field_mapping_status: string[];
  academic_field_v2_branches: AcademicFieldV2Branch[];
  stem_flag: boolean | null;
  selection_category: string[];
  exclusive_enrollment_status: string[];
  school_recommendation_required: string[];
  academic_record_required: string[];
  common_test_required: string[];
  research_requirement_required: string[];
  research_activity_level_status: string[];
  selection_interview: string[];
  selection_oral_exam: string[];
  selection_presentation: string[];
  selection_essay: string[];
  selection_written_exam: string[];
  selection_common_test: string[];
  english_requirement_status: string[];
  gpa_tenths: number | null;
  gpa_mode: "safe" | "review" | "all";
  grade_requirement_status: "required" | null;
  overall_gpa_tenths: number | null;
  page: number;
}

export interface AcademicFieldV2Branch {
  group_code: string;
  subcategory_codes: string[];
}

export type GpaDerivedStatus = "safe match" | "safe no match" | "safe numeric rule (GPA not supplied)" | "conditional/review required" | "not numerically evaluable";

export interface SearchSummary {
  total_matched_rows: number;
  gpa_safe_match_rows: number | null;
  gpa_safe_no_match_rows: number | null;
  gpa_safe_numeric_rule_rows: number;
  gpa_conditional_review_rows: number;
  gpa_not_numerically_evaluable_rows: number;
  rows_by_source_dataset: Record<string, number>;
  university_count: number;
}

export interface SearchResult { rows: SearchRow[]; summary: SearchSummary; }

export interface DetailRecord {
  site_data_schema_version: "0.2";
  identity: { source_dataset: string; source_version: string; record_id: string };
  admission: Record<string, Scalar>;
  gpa_derived: Record<string, Scalar>;
  grade_requirement_derived: Record<string, Scalar>;
  academic_field_derived: Record<string, Scalar | Array<Record<string, Scalar>>>;
  academic_field_v2_derived: Record<string, Scalar | Array<Record<string, Scalar>>>;
  english_requirement_derived: Record<string, Scalar>;
  research_requirements: Array<Record<string, Scalar>>;
}
