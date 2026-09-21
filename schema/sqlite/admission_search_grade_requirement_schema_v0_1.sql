PRAGMA foreign_keys = ON;

CREATE TABLE admission_search_grade_requirements (
    admission_rowid INTEGER PRIMARY KEY
        REFERENCES admissions(admission_rowid) ON DELETE CASCADE,
    raw_value TEXT,
    grade_requirement_status TEXT NOT NULL CHECK (
        grade_requirement_status IN (
            'required', 'not_required', 'review_required', 'unknown',
            'not_applicable', 'unmapped'
        )
    ),
    overall_gpa_min_tenths INTEGER CHECK (
        overall_gpa_min_tenths BETWEEN 0 AND 50
    ),
    overall_gpa_min_inclusive INTEGER CHECK (
        overall_gpa_min_inclusive IN (0, 1)
    ),
    overall_gpa_status TEXT NOT NULL CHECK (
        overall_gpa_status IN (
            'safe_simple_overall',
            'safe_overall_with_additional_conditions',
            'no_safe_overall_floor', 'historical', 'non_binding',
            'non_admission_numeric', 'ambiguous', 'unknown',
            'not_applicable', 'unmapped'
        )
    ),
    additional_grade_conditions INTEGER CHECK (
        additional_grade_conditions IN (0, 1)
    ),
    parse_status TEXT NOT NULL CHECK (
        parse_status IN ('exact_crosswalk', 'missing', 'unmapped')
    ),
    mapping_contract_version TEXT NOT NULL
        CHECK (mapping_contract_version = '0.1'),
    review_note TEXT,
    CHECK (
        (overall_gpa_min_tenths IS NULL
         AND overall_gpa_min_inclusive IS NULL
         AND additional_grade_conditions IS NULL)
        OR
        (grade_requirement_status = 'required'
         AND overall_gpa_min_tenths IS NOT NULL
         AND overall_gpa_min_inclusive = 1
         AND additional_grade_conditions IS NOT NULL
         AND overall_gpa_status IN (
             'safe_simple_overall',
             'safe_overall_with_additional_conditions'
         ))
    ),
    CHECK (
        overall_gpa_status <> 'safe_simple_overall'
        OR additional_grade_conditions = 0
    ),
    CHECK (
        overall_gpa_status <> 'safe_overall_with_additional_conditions'
        OR additional_grade_conditions = 1
    ),
    CHECK (
        raw_value IS NOT NULL OR (
            grade_requirement_status = 'unknown'
            AND overall_gpa_status = 'unknown'
            AND parse_status = 'missing'
        )
    ),
    CHECK (
        grade_requirement_status <> 'unmapped'
        OR (overall_gpa_status = 'unmapped' AND parse_status = 'unmapped')
    )
) STRICT;

CREATE INDEX idx_grade_requirement_status
ON admission_search_grade_requirements(
    grade_requirement_status, admission_rowid
);

CREATE INDEX idx_grade_requirement_overall_gpa
ON admission_search_grade_requirements(
    overall_gpa_min_tenths, admission_rowid
)
WHERE grade_requirement_status = 'required'
  AND overall_gpa_min_tenths IS NOT NULL;

CREATE VIEW admission_search_grade_requirements_safe AS
SELECT
    admission_rowid,
    raw_value,
    overall_gpa_min_tenths,
    overall_gpa_min_inclusive,
    overall_gpa_status,
    additional_grade_conditions
FROM admission_search_grade_requirements
WHERE grade_requirement_status = 'required'
  AND parse_status = 'exact_crosswalk'
  AND overall_gpa_min_tenths IS NOT NULL
  AND overall_gpa_min_inclusive = 1;
