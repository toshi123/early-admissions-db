PRAGMA foreign_keys = ON;

CREATE TABLE admission_search_english_requirement (
    admission_rowid INTEGER PRIMARY KEY
        REFERENCES admissions(admission_rowid) ON DELETE CASCADE,
    raw_value TEXT,
    requirement_status TEXT NOT NULL CHECK (
        requirement_status IN (
            'required', 'not_required', 'review_required', 'unknown',
            'not_applicable', 'unmapped'
        )
    ),
    parse_status TEXT NOT NULL CHECK (
        parse_status IN ('exact_crosswalk', 'missing', 'unmapped')
    ),
    search_disposition TEXT NOT NULL CHECK (
        search_disposition IN ('safe_exact', 'review_required', 'not_searchable')
    ),
    parser_contract_version TEXT NOT NULL
        CHECK (parser_contract_version = '0.3'),
    review_note TEXT,
    CHECK (raw_value IS NOT NULL OR (
        requirement_status = 'unknown' AND parse_status = 'missing'
        AND search_disposition = 'not_searchable'
    )),
    CHECK (requirement_status NOT IN ('required', 'not_required')
           OR (parse_status = 'exact_crosswalk' AND search_disposition = 'safe_exact')),
    CHECK (requirement_status <> 'unmapped'
           OR (parse_status = 'unmapped' AND search_disposition = 'review_required'))
) STRICT;

CREATE INDEX idx_admission_search_english_requirement_status
ON admission_search_english_requirement(requirement_status, admission_rowid);

CREATE VIEW admission_search_english_requirement_safe AS
SELECT admission_rowid, raw_value, requirement_status
FROM admission_search_english_requirement
WHERE parse_status = 'exact_crosswalk'
  AND search_disposition = 'safe_exact'
  AND requirement_status IN ('required', 'not_required');
