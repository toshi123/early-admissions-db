-- Early Admissions SQLite schema v0.3 (Unified contract v0.3)
--
-- This is a design contract. It does not create a database file by itself.
-- The builder must enable PRAGMA foreign_keys before loading any rows and must
-- load empty unified CSV cells as SQL NULL, never as an empty string.
--
-- The active FTS profile uses FTS5 trigram because it is available in the
-- verified build environment. See docs/sqlite_design_v0_1.md for capability
-- probing and portable fallback profiles.

PRAGMA foreign_keys = ON;

BEGIN;

CREATE TABLE admissions (
    admission_rowid INTEGER PRIMARY KEY,
    source_dataset TEXT NOT NULL
        CHECK (source_dataset IN ('kokkoritsu', 'shidai')),
    source_version TEXT NOT NULL
        CHECK (source_version IN ('5.83', '1.10')),
    record_id TEXT NOT NULL CHECK (record_id <> ''),
    admission_year INTEGER NOT NULL CHECK (admission_year = 2027),
    institution_type TEXT NOT NULL
        CHECK (institution_type IN ('国立', '公立', '私立')),
    university TEXT NOT NULL CHECK (university <> ''),
    prefecture TEXT,
    academic_field TEXT,
    stem_flag INTEGER CHECK (stem_flag IN (0, 1)),
    faculty_school TEXT,
    department TEXT,
    selection_category TEXT,
    selection_name TEXT,
    slot_type TEXT,
    international_baccalaureate_flag INTEGER NOT NULL
        CHECK (international_baccalaureate_flag IN (0, 1)),
    private_foreign_student_flag INTEGER NOT NULL
        CHECK (private_foreign_student_flag IN (0, 1)),
    returnee_flag INTEGER NOT NULL
        CHECK (returnee_flag IN (0, 1)),
    regional_quota_flag INTEGER NOT NULL
        CHECK (regional_quota_flag IN (0, 1)),
    adult_selection_flag INTEGER NOT NULL
        CHECK (adult_selection_flag IN (0, 1)),
    capacity TEXT,
    school_recommendation_required TEXT
        CHECK (school_recommendation_required IN ('Yes', 'No', 'Unknown')),
    school_nomination_limit TEXT,
    school_nomination_limit_total TEXT,
    school_nomination_limit_rule TEXT,
    exclusive_enrollment_status TEXT NOT NULL
        CHECK (exclusive_enrollment_status IN ('専願', '併願可', '条件付き', '不明')),
    exclusive_enrollment TEXT,
    exclusive_enrollment_evidence TEXT,
    exclusive_enrollment_evidence_page TEXT,
    exclusive_enrollment_evidence_url TEXT,
    eligibility_graduation TEXT,
    gpa_requirement TEXT,
    english_requirement TEXT,
    subject_prerequisites TEXT,
    common_test_required TEXT
        CHECK (common_test_required IN ('Yes', 'No', 'Unknown', 'Conditional')),
    common_test_usage TEXT,
    research_activity_level_status TEXT
        CHECK (
            research_activity_level_status IN
                ('required', 'relevant', 'none', 'unknown', 'unmapped')
        ),
    research_activity_level_raw TEXT,
    research_requirement_required TEXT
        CHECK (research_requirement_required IN ('Yes', 'No', 'Unknown')),
    research_activity_detail TEXT,
    research_requirement_summary TEXT,
    academic_record_required TEXT
        CHECK (academic_record_required IN ('Yes', 'No', 'Unknown')),
    academic_record_type TEXT,
    academic_record_detail TEXT,
    documents_summary TEXT,
    selection_process TEXT,
    selection_document_review TEXT
        CHECK (selection_document_review IN ('Yes', 'No', 'Unknown')),
    selection_interview TEXT
        CHECK (selection_interview IN ('Yes', 'No', 'Unknown')),
    selection_oral_exam TEXT
        CHECK (selection_oral_exam IN ('Yes', 'No', 'Unknown')),
    selection_presentation TEXT
        CHECK (selection_presentation IN ('Yes', 'No', 'Unknown')),
    selection_essay TEXT
        CHECK (selection_essay IN ('Yes', 'No', 'Unknown')),
    selection_written_exam TEXT
        CHECK (selection_written_exam IN ('Yes', 'No', 'Unknown')),
    selection_practical TEXT
        CHECK (selection_practical IN ('Yes', 'No', 'Unknown')),
    selection_group_discussion TEXT
        CHECK (selection_group_discussion IN ('Yes', 'No', 'Unknown')),
    selection_aptitude_test TEXT
        CHECK (selection_aptitude_test IN ('Yes', 'No', 'Unknown')),
    selection_common_test TEXT
        CHECK (selection_common_test IN ('Yes', 'No', 'Unknown')),
    interview_detail TEXT,
    oral_exam_subjects TEXT,
    oral_exam_detail TEXT,
    presentation_detail TEXT,
    essay_detail TEXT,
    written_exam_detail TEXT,
    selection_method_detail TEXT,
    application_start TEXT,
    application_end TEXT,
    web_registration_period TEXT,
    first_stage_result_date TEXT,
    second_stage_start TEXT,
    second_stage_end TEXT,
    final_result_date TEXT,
    source_status TEXT,
    detail_completeness_status TEXT
        CHECK (
            detail_completeness_status IN
                ('complete', 'partial', 'pending', 'unknown', 'unmapped')
        ),
    detail_completeness_raw TEXT,
    verification_grade TEXT
        CHECK (verification_grade IN ('A', 'B', 'C')),
    verified_on TEXT NOT NULL CHECK (verified_on <> ''),
    source_url TEXT NOT NULL CHECK (source_url <> ''),
    schedule_url TEXT,
    guideline_url TEXT,
    notes TEXT,
    information_year INTEGER,
    publication_status TEXT,
    fallback_previous_year INTEGER
        CHECK (fallback_previous_year IN (0, 1)),
    current_year_release_expected TEXT,
    previous_year_source_url TEXT,
    fallback_note TEXT,

    UNIQUE (source_dataset, source_version, record_id),
    CHECK (
        (source_dataset = 'kokkoritsu' AND source_version = '5.83') OR
        (source_dataset = 'shidai' AND source_version = '1.10')
    ),
    CHECK (
        (source_dataset = 'kokkoritsu' AND institution_type IN ('国立', '公立')) OR
        (source_dataset = 'shidai' AND institution_type = '私立')
    )
) STRICT;

CREATE TABLE coverage (
    coverage_rowid INTEGER PRIMARY KEY,
    source_dataset TEXT NOT NULL
        CHECK (source_dataset IN ('kokkoritsu', 'shidai')),
    source_version TEXT NOT NULL
        CHECK (source_version IN ('5.83', '1.10')),
    institution_type TEXT NOT NULL
        CHECK (institution_type IN ('国立', '公立', '私立')),
    university TEXT NOT NULL CHECK (university <> ''),
    undergraduate_scope TEXT,
    research_status TEXT,
    master_rows INTEGER NOT NULL CHECK (master_rows >= 0),
    current_year_status TEXT,
    fallback_status TEXT,
    checked_on TEXT NOT NULL CHECK (checked_on <> ''),
    official_source_url TEXT,
    notes TEXT,

    UNIQUE (source_dataset, source_version, institution_type, university),
    CHECK (
        (source_dataset = 'kokkoritsu' AND source_version = '5.83') OR
        (source_dataset = 'shidai' AND source_version = '1.10')
    ),
    CHECK (
        (source_dataset = 'kokkoritsu' AND institution_type IN ('国立', '公立')) OR
        (source_dataset = 'shidai' AND institution_type = '私立')
    )
) STRICT;

CREATE TABLE research_requirements (
    research_rowid INTEGER PRIMARY KEY,
    source_dataset TEXT NOT NULL
        CHECK (source_dataset IN ('kokkoritsu', 'shidai')),
    source_version TEXT NOT NULL
        CHECK (source_version IN ('5.83', '1.10')),
    admission_id TEXT NOT NULL CHECK (admission_id <> ''),
    university TEXT NOT NULL CHECK (university <> ''),
    faculty_school TEXT,
    department TEXT,
    selection_name TEXT,
    requirement_code TEXT,
    program_or_competition TEXT,
    required_level TEXT,
    requirement_detail TEXT,
    alternative_allowed TEXT,
    evidence_required TEXT,
    source_url TEXT NOT NULL CHECK (source_url <> ''),
    verified_on TEXT NOT NULL CHECK (verified_on <> ''),

    CHECK (
        (source_dataset = 'kokkoritsu' AND source_version = '5.83') OR
        (source_dataset = 'shidai' AND source_version = '1.10')
    ),
    FOREIGN KEY (source_dataset, source_version, admission_id)
        REFERENCES admissions (source_dataset, source_version, record_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT
) STRICT;

-- Exactly one row per generated database. JSON-valued metadata columns use
-- canonical JSON text; the future builder validates their object shape before
-- commit rather than requiring the optional json_valid() SQL function.
CREATE TABLE build_metadata (
    singleton_id INTEGER PRIMARY KEY CHECK (singleton_id = 1),
    database_schema_version TEXT NOT NULL
        CHECK (database_schema_version = '0.3'),
    unified_contract_version TEXT NOT NULL
        CHECK (unified_contract_version = '0.3'),
    unified_schema_id TEXT NOT NULL CHECK (unified_schema_id <> ''),
    build_timestamp_utc TEXT NOT NULL CHECK (build_timestamp_utc <> ''),
    builder_version TEXT NOT NULL CHECK (builder_version <> ''),
    validation_profile TEXT NOT NULL
        CHECK (validation_profile IN ('production', 'candidate_audit')),
    review_required_counts_json TEXT NOT NULL
        CHECK (review_required_counts_json <> ''),
    sqlite_library_version TEXT NOT NULL CHECK (sqlite_library_version <> ''),
    fts5_enabled INTEGER NOT NULL CHECK (fts5_enabled IN (0, 1)),
    fts_tokenizer TEXT NOT NULL
        CHECK (fts_tokenizer IN ('trigram', 'unicode61', 'none')),
    source_versions_json TEXT NOT NULL CHECK (source_versions_json <> ''),
    input_csv_sha256_json TEXT NOT NULL CHECK (input_csv_sha256_json <> ''),
    input_build_manifest_sha256 TEXT NOT NULL
        CHECK (
            length(input_build_manifest_sha256) = 64 AND
            input_build_manifest_sha256 NOT GLOB '*[^0-9a-f]*'
        ),
    schema_sql_sha256 TEXT NOT NULL
        CHECK (
            length(schema_sql_sha256) = 64 AND
            schema_sql_sha256 NOT GLOB '*[^0-9a-f]*'
        ),
    gpa_parser_contract_version TEXT NOT NULL
        CHECK (gpa_parser_contract_version = '0.1'),
    gpa_schema_sql_sha256 TEXT NOT NULL
        CHECK (
            length(gpa_schema_sql_sha256) = 64 AND
            gpa_schema_sql_sha256 NOT GLOB '*[^0-9a-f]*'
        ),
    gpa_crosswalk_sha256 TEXT NOT NULL
        CHECK (
            length(gpa_crosswalk_sha256) = 64 AND
            gpa_crosswalk_sha256 NOT GLOB '*[^0-9a-f]*'
        ),
    grade_requirement_mapping_contract_version TEXT NOT NULL
        CHECK (grade_requirement_mapping_contract_version = '0.3'),
    grade_requirement_schema_sql_sha256 TEXT NOT NULL
        CHECK (
            length(grade_requirement_schema_sql_sha256) = 64 AND
            grade_requirement_schema_sql_sha256 NOT GLOB '*[^0-9a-f]*'
        ),
    grade_requirement_crosswalk_sha256 TEXT NOT NULL
        CHECK (
            length(grade_requirement_crosswalk_sha256) = 64 AND
            grade_requirement_crosswalk_sha256 NOT GLOB '*[^0-9a-f]*'
        ),
    grade_requirement_classification_counts_json TEXT NOT NULL
        CHECK (grade_requirement_classification_counts_json <> ''),
    grade_requirement_overall_status_counts_json TEXT NOT NULL
        CHECK (grade_requirement_overall_status_counts_json <> ''),
    grade_requirement_numeric_floor_rows INTEGER NOT NULL
        CHECK (grade_requirement_numeric_floor_rows >= 0),
    grade_requirement_raw_mismatch_rows INTEGER NOT NULL
        CHECK (grade_requirement_raw_mismatch_rows = 0),
    academic_field_mapping_contract_version TEXT NOT NULL
        CHECK (academic_field_mapping_contract_version = '0.3'),
    academic_field_taxonomy_version TEXT NOT NULL
        CHECK (academic_field_taxonomy_version = '0.1'),
    academic_field_schema_sql_sha256 TEXT NOT NULL
        CHECK (
            length(academic_field_schema_sql_sha256) = 64 AND
            academic_field_schema_sql_sha256 NOT GLOB '*[^0-9a-f]*'
        ),
    academic_field_taxonomy_sha256 TEXT NOT NULL
        CHECK (
            length(academic_field_taxonomy_sha256) = 64 AND
            academic_field_taxonomy_sha256 NOT GLOB '*[^0-9a-f]*'
        ),
    academic_field_crosswalk_sha256 TEXT NOT NULL
        CHECK (
            length(academic_field_crosswalk_sha256) = 64 AND
            academic_field_crosswalk_sha256 NOT GLOB '*[^0-9a-f]*'
        ),
    english_requirement_parser_contract_version TEXT NOT NULL
        CHECK (english_requirement_parser_contract_version = '0.3'),
    english_requirement_schema_sql_sha256 TEXT NOT NULL
        CHECK (length(english_requirement_schema_sql_sha256) = 64),
    english_requirement_crosswalk_sha256 TEXT NOT NULL
        CHECK (length(english_requirement_crosswalk_sha256) = 64),
    english_requirement_required_rows INTEGER NOT NULL CHECK (english_requirement_required_rows >= 0),
    english_requirement_not_required_rows INTEGER NOT NULL CHECK (english_requirement_not_required_rows >= 0),
    english_requirement_review_required_rows INTEGER NOT NULL CHECK (english_requirement_review_required_rows >= 0),
    english_requirement_unknown_rows INTEGER NOT NULL CHECK (english_requirement_unknown_rows >= 0),
    english_requirement_not_applicable_rows INTEGER NOT NULL CHECK (english_requirement_not_applicable_rows >= 0),
    english_requirement_unmapped_rows INTEGER NOT NULL CHECK (english_requirement_unmapped_rows >= 0),
    prefecture_mapping_contract_version TEXT NOT NULL CHECK(prefecture_mapping_contract_version='0.1'),
    prefecture_taxonomy_version TEXT NOT NULL CHECK(prefecture_taxonomy_version='0.1'),
    prefecture_schema_sql_sha256 TEXT NOT NULL CHECK(length(prefecture_schema_sql_sha256)=64),
    prefecture_taxonomy_sha256 TEXT NOT NULL CHECK(length(prefecture_taxonomy_sha256)=64),
    prefecture_crosswalk_sha256 TEXT NOT NULL CHECK(length(prefecture_crosswalk_sha256)=64),
    prefecture_parent_rows INTEGER NOT NULL CHECK(prefecture_parent_rows>=0),
    prefecture_membership_rows INTEGER NOT NULL CHECK(prefecture_membership_rows>=0),
    prefecture_single_rows INTEGER NOT NULL CHECK(prefecture_single_rows>=0),
    prefecture_multi_rows INTEGER NOT NULL CHECK(prefecture_multi_rows>=0),
    prefecture_unmapped_rows INTEGER NOT NULL CHECK(prefecture_unmapped_rows>=0),
    admissions_rows INTEGER NOT NULL CHECK (admissions_rows >= 0),
    coverage_rows INTEGER NOT NULL CHECK (coverage_rows >= 0),
    research_requirements_rows INTEGER NOT NULL
        CHECK (research_requirements_rows >= 0),
    gpa_safe_numeric_rows INTEGER NOT NULL CHECK (gpa_safe_numeric_rows >= 0),
    gpa_conditional_numeric_rows INTEGER NOT NULL
        CHECK (gpa_conditional_numeric_rows >= 0),
    gpa_do_not_numeric_rows INTEGER NOT NULL
        CHECK (gpa_do_not_numeric_rows >= 0),
    gpa_strict_match_3_8_rows INTEGER NOT NULL
        CHECK (gpa_strict_match_3_8_rows >= 0),
    academic_field_parent_rows INTEGER NOT NULL
        CHECK (academic_field_parent_rows >= 0),
    academic_field_group_rows INTEGER NOT NULL
        CHECK (academic_field_group_rows >= 0),
    academic_field_single_rows INTEGER NOT NULL
        CHECK (academic_field_single_rows >= 0),
    academic_field_multi_rows INTEGER NOT NULL
        CHECK (academic_field_multi_rows >= 0),
    academic_field_review_required_rows INTEGER NOT NULL
        CHECK (academic_field_review_required_rows >= 0),
    academic_field_unmapped_rows INTEGER NOT NULL
        CHECK (academic_field_unmapped_rows >= 0),
    academic_field_not_applicable_rows INTEGER NOT NULL
        CHECK (academic_field_not_applicable_rows >= 0),
    academic_field_raw_mismatch_rows INTEGER NOT NULL
        CHECK (academic_field_raw_mismatch_rows = 0),
    academic_field_v2_mapping_contract_version TEXT NOT NULL
        CHECK (academic_field_v2_mapping_contract_version = '0.4'),
    academic_field_v2_taxonomy_version TEXT NOT NULL
        CHECK (academic_field_v2_taxonomy_version = '0.2'),
    academic_field_v2_schema_sql_sha256 TEXT NOT NULL
        CHECK (length(academic_field_v2_schema_sql_sha256) = 64),
    academic_field_v2_broad_taxonomy_sha256 TEXT NOT NULL
        CHECK (length(academic_field_v2_broad_taxonomy_sha256) = 64),
    academic_field_v2_subcategory_taxonomy_sha256 TEXT NOT NULL
        CHECK (length(academic_field_v2_subcategory_taxonomy_sha256) = 64),
    academic_field_v2_raw_crosswalk_sha256 TEXT NOT NULL
        CHECK (length(academic_field_v2_raw_crosswalk_sha256) = 64),
    academic_field_v2_context_crosswalk_sha256 TEXT NOT NULL
        CHECK (length(academic_field_v2_context_crosswalk_sha256) = 64),
    academic_field_v2_compatibility_crosswalk_sha256 TEXT NOT NULL
        CHECK (length(academic_field_v2_compatibility_crosswalk_sha256) = 64),
    academic_field_v2_broad_taxonomy_rows INTEGER NOT NULL
        CHECK (academic_field_v2_broad_taxonomy_rows >= 0),
    academic_field_v2_subcategory_taxonomy_rows INTEGER NOT NULL
        CHECK (academic_field_v2_subcategory_taxonomy_rows >= 0),
    academic_field_v2_parent_rows INTEGER NOT NULL
        CHECK (academic_field_v2_parent_rows >= 0),
    academic_field_v2_broad_membership_rows INTEGER NOT NULL
        CHECK (academic_field_v2_broad_membership_rows >= 0),
    academic_field_v2_subcategory_membership_rows INTEGER NOT NULL
        CHECK (academic_field_v2_subcategory_membership_rows >= 0),
    academic_field_v2_broad_review_required_rows INTEGER NOT NULL
        CHECK (academic_field_v2_broad_review_required_rows >= 0),
    academic_field_v2_subcategory_review_required_rows INTEGER NOT NULL
        CHECK (academic_field_v2_subcategory_review_required_rows >= 0),
    academic_field_v2_unmapped_rows INTEGER NOT NULL
        CHECK (academic_field_v2_unmapped_rows >= 0),
    academic_field_v2_raw_mismatch_rows INTEGER NOT NULL
        CHECK (academic_field_v2_raw_mismatch_rows = 0),
    CHECK (
        (fts5_enabled = 1 AND fts_tokenizer IN ('trigram', 'unicode61')) OR
        (fts5_enabled = 0 AND fts_tokenizer = 'none')
    )
) STRICT;

-- Reserved derived layer. The base v0.1 raw date/period strings always remain
-- in admissions. Rows must not be populated until a separate normalized-date
-- parser contract is approved. A single date is represented by equal start/end.
CREATE TABLE admission_search_dates (
    admission_rowid INTEGER NOT NULL,
    source_field TEXT NOT NULL
        CHECK (
            source_field IN (
                'application_start',
                'application_end',
                'web_registration_period',
                'first_stage_result_date',
                'second_stage_start',
                'second_stage_end',
                'final_result_date'
            )
        ),
    date_start TEXT,
    date_end TEXT,
    parse_status TEXT NOT NULL
        CHECK (parse_status IN ('parsed', 'partial', 'unparsed', 'not_applicable')),
    PRIMARY KEY (admission_rowid, source_field),
    CHECK (date_start IS NULL OR date_start GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    CHECK (date_end IS NULL OR date_end GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    CHECK (parse_status <> 'parsed' OR (date_start IS NOT NULL AND date_end IS NOT NULL)),
    FOREIGN KEY (admission_rowid)
        REFERENCES admissions (admission_rowid)
        ON UPDATE RESTRICT
        ON DELETE CASCADE
) STRICT;

-- Identity, drill-down, and common guidance-query indexes. Low-cardinality
-- flags are grouped into narrow covering indexes rather than receiving one
-- full index each. Run ANALYZE after the completed bulk load.
CREATE INDEX idx_admissions_university
    ON admissions (university, faculty_school, department);

CREATE INDEX idx_admissions_institution_prefecture
    ON admissions (institution_type, prefecture, university);

CREATE INDEX idx_admissions_stem_academic
    ON admissions (stem_flag, academic_field, institution_type, prefecture, university);

CREATE INDEX idx_admissions_selection_category
    ON admissions (selection_category, institution_type, university);

CREATE INDEX idx_admissions_exclusive_enrollment
    ON admissions (exclusive_enrollment_status, institution_type, prefecture, university);

CREATE INDEX idx_admissions_recommendation_record
    ON admissions (
        school_recommendation_required,
        academic_record_required,
        institution_type,
        university
    );

CREATE INDEX idx_admissions_common_research
    ON admissions (
        common_test_required,
        research_requirement_required,
        institution_type,
        university
    );

CREATE INDEX idx_admissions_interview_oral_presentation
    ON admissions (
        selection_interview,
        selection_oral_exam,
        selection_presentation,
        admission_rowid
    );

CREATE INDEX idx_admissions_common_essay_written
    ON admissions (
        selection_common_test,
        selection_essay,
        selection_written_exam,
        admission_rowid
    );

CREATE INDEX idx_research_requirements_admission
    ON research_requirements (
        source_dataset,
        source_version,
        admission_id,
        research_rowid
    );

CREATE INDEX idx_admission_search_dates_range
    ON admission_search_dates (source_field, date_start, date_end, admission_rowid);

-- One row per admission. Child multiplicity is represented only as a count;
-- no child values are concatenated or discarded here.
CREATE VIEW admissions_search AS
SELECT
    a.*,
    c.undergraduate_scope AS coverage_undergraduate_scope,
    c.research_status AS coverage_research_status,
    c.master_rows AS coverage_master_rows,
    c.current_year_status AS coverage_current_year_status,
    c.fallback_status AS coverage_fallback_status,
    c.checked_on AS coverage_checked_on,
    c.official_source_url AS coverage_official_source_url,
    c.notes AS coverage_notes,
    COALESCE(rr.research_detail_rows, 0) AS research_detail_rows,
    CASE WHEN rr.research_detail_rows IS NULL THEN 0 ELSE 1 END AS has_research_details
FROM admissions AS a
LEFT JOIN coverage AS c
    ON c.source_dataset = a.source_dataset
   AND c.source_version = a.source_version
   AND c.institution_type = a.institution_type
   AND c.university = a.university
LEFT JOIN (
    SELECT
        source_dataset,
        source_version,
        admission_id,
        COUNT(*) AS research_detail_rows
    FROM research_requirements
    GROUP BY source_dataset, source_version, admission_id
) AS rr
    ON rr.source_dataset = a.source_dataset
   AND rr.source_version = a.source_version
   AND rr.admission_id = a.record_id;

-- One row per admission-child pair. Exact duplicate child facts remain visible
-- as separate rows because each source row has a distinct research_rowid.
-- Admissions with no child row still appear once with NULL research_* columns.
CREATE VIEW admissions_with_research AS
SELECT
    a.*,
    r.research_rowid,
    r.admission_id AS research_admission_id,
    r.university AS research_university,
    r.faculty_school AS research_faculty_school,
    r.department AS research_department,
    r.selection_name AS research_selection_name,
    r.requirement_code AS research_requirement_code,
    r.program_or_competition AS research_program_or_competition,
    r.required_level AS research_required_level,
    r.requirement_detail AS research_requirement_detail,
    r.alternative_allowed AS research_alternative_allowed,
    r.evidence_required AS research_evidence_required,
    r.source_url AS research_source_url,
    r.verified_on AS research_verified_on
FROM admissions AS a
LEFT JOIN research_requirements AS r
    ON r.source_dataset = a.source_dataset
   AND r.source_version = a.source_version
   AND r.admission_id = a.record_id;

-- Recommended full-text profile for the verified environment.
-- The FTS table is external-content: admissions remains authoritative, while
-- FTS stores its own index and obtains result text from admissions by rowid.
-- BEGIN OPTIONAL FTS5 PROFILE
CREATE VIRTUAL TABLE admissions_fts USING fts5(
    university,
    faculty_school,
    department,
    selection_name,
    academic_field,
    eligibility_graduation,
    gpa_requirement,
    english_requirement,
    subject_prerequisites,
    research_activity_detail,
    research_requirement_summary,
    documents_summary,
    selection_process,
    interview_detail,
    oral_exam_subjects,
    oral_exam_detail,
    presentation_detail,
    essay_detail,
    written_exam_detail,
    selection_method_detail,
    content = 'admissions',
    content_rowid = 'admission_rowid',
    tokenize = 'trigram'
);

CREATE TRIGGER admissions_fts_ai AFTER INSERT ON admissions BEGIN
    INSERT INTO admissions_fts (
        rowid,
        university,
        faculty_school,
        department,
        selection_name,
        academic_field,
        eligibility_graduation,
        gpa_requirement,
        english_requirement,
        subject_prerequisites,
        research_activity_detail,
        research_requirement_summary,
        documents_summary,
        selection_process,
        interview_detail,
        oral_exam_subjects,
        oral_exam_detail,
        presentation_detail,
        essay_detail,
        written_exam_detail,
        selection_method_detail
    ) VALUES (
        new.admission_rowid,
        new.university,
        new.faculty_school,
        new.department,
        new.selection_name,
        new.academic_field,
        new.eligibility_graduation,
        new.gpa_requirement,
        new.english_requirement,
        new.subject_prerequisites,
        new.research_activity_detail,
        new.research_requirement_summary,
        new.documents_summary,
        new.selection_process,
        new.interview_detail,
        new.oral_exam_subjects,
        new.oral_exam_detail,
        new.presentation_detail,
        new.essay_detail,
        new.written_exam_detail,
        new.selection_method_detail
    );
END;

CREATE TRIGGER admissions_fts_ad AFTER DELETE ON admissions BEGIN
    INSERT INTO admissions_fts (
        admissions_fts,
        rowid,
        university,
        faculty_school,
        department,
        selection_name,
        academic_field,
        eligibility_graduation,
        gpa_requirement,
        english_requirement,
        subject_prerequisites,
        research_activity_detail,
        research_requirement_summary,
        documents_summary,
        selection_process,
        interview_detail,
        oral_exam_subjects,
        oral_exam_detail,
        presentation_detail,
        essay_detail,
        written_exam_detail,
        selection_method_detail
    ) VALUES (
        'delete',
        old.admission_rowid,
        old.university,
        old.faculty_school,
        old.department,
        old.selection_name,
        old.academic_field,
        old.eligibility_graduation,
        old.gpa_requirement,
        old.english_requirement,
        old.subject_prerequisites,
        old.research_activity_detail,
        old.research_requirement_summary,
        old.documents_summary,
        old.selection_process,
        old.interview_detail,
        old.oral_exam_subjects,
        old.oral_exam_detail,
        old.presentation_detail,
        old.essay_detail,
        old.written_exam_detail,
        old.selection_method_detail
    );
END;

CREATE TRIGGER admissions_fts_au AFTER UPDATE ON admissions BEGIN
    INSERT INTO admissions_fts (
        admissions_fts,
        rowid,
        university,
        faculty_school,
        department,
        selection_name,
        academic_field,
        eligibility_graduation,
        gpa_requirement,
        english_requirement,
        subject_prerequisites,
        research_activity_detail,
        research_requirement_summary,
        documents_summary,
        selection_process,
        interview_detail,
        oral_exam_subjects,
        oral_exam_detail,
        presentation_detail,
        essay_detail,
        written_exam_detail,
        selection_method_detail
    ) VALUES (
        'delete',
        old.admission_rowid,
        old.university,
        old.faculty_school,
        old.department,
        old.selection_name,
        old.academic_field,
        old.eligibility_graduation,
        old.gpa_requirement,
        old.english_requirement,
        old.subject_prerequisites,
        old.research_activity_detail,
        old.research_requirement_summary,
        old.documents_summary,
        old.selection_process,
        old.interview_detail,
        old.oral_exam_subjects,
        old.oral_exam_detail,
        old.presentation_detail,
        old.essay_detail,
        old.written_exam_detail,
        old.selection_method_detail
    );
    INSERT INTO admissions_fts (
        rowid,
        university,
        faculty_school,
        department,
        selection_name,
        academic_field,
        eligibility_graduation,
        gpa_requirement,
        english_requirement,
        subject_prerequisites,
        research_activity_detail,
        research_requirement_summary,
        documents_summary,
        selection_process,
        interview_detail,
        oral_exam_subjects,
        oral_exam_detail,
        presentation_detail,
        essay_detail,
        written_exam_detail,
        selection_method_detail
    ) VALUES (
        new.admission_rowid,
        new.university,
        new.faculty_school,
        new.department,
        new.selection_name,
        new.academic_field,
        new.eligibility_graduation,
        new.gpa_requirement,
        new.english_requirement,
        new.subject_prerequisites,
        new.research_activity_detail,
        new.research_requirement_summary,
        new.documents_summary,
        new.selection_process,
        new.interview_detail,
        new.oral_exam_subjects,
        new.oral_exam_detail,
        new.presentation_detail,
        new.essay_detail,
        new.written_exam_detail,
        new.selection_method_detail
    );
END;
-- END OPTIONAL FTS5 PROFILE

COMMIT;

-- Portable fallback profiles (not executed by this file):
--
-- 1. FTS5 present but trigram unavailable:
--      replace tokenize = 'trigram' above with tokenize = 'unicode61'.
--    Japanese substring quality is reduced; use escaped LIKE for substring
--    queries and record fts_tokenizer='unicode61' in build_metadata.
--
-- 2. FTS5 unavailable:
--      omit admissions_fts and its three triggers, use escaped LIKE against
--      admissions, and record fts5_enabled=0 / fts_tokenizer='none'.
