-- GPA search derived-layer schema contract v0.1.
--
-- Applied by the reproducible SQLite builder after the base schema.
-- admissions.gpa_requirement remains authoritative raw source text.

PRAGMA foreign_keys = ON;

-- One classification row per admissions row.  The generic gpa_min/gpa_max
-- columns are intentionally populated only for a complete, unconditional,
-- current-year, overall-GPA rule.  Numeric fragments from compound rules must
-- never be copied into these columns.
CREATE TABLE admission_search_gpa (
    admission_rowid INTEGER PRIMARY KEY,
    raw_value TEXT,
    gpa_min_tenths INTEGER,
    gpa_min REAL GENERATED ALWAYS AS (
        CASE
            WHEN gpa_min_tenths IS NULL THEN NULL
            ELSE gpa_min_tenths / 10.0
        END
    ) VIRTUAL,
    gpa_min_inclusive INTEGER
        CHECK (gpa_min_inclusive IN (0, 1)),
    gpa_max_tenths INTEGER,
    gpa_max REAL GENERATED ALWAYS AS (
        CASE
            WHEN gpa_max_tenths IS NULL THEN NULL
            ELSE gpa_max_tenths / 10.0
        END
    ) VIRTUAL,
    gpa_max_inclusive INTEGER
        CHECK (gpa_max_inclusive IN (0, 1)),
    gpa_scale TEXT NOT NULL
        CHECK (gpa_scale IN ('japanese_5_point', 'other', 'unknown')),
    metric_scope TEXT NOT NULL
        CHECK (metric_scope IN ('overall', 'subject', 'mixed', 'none', 'unknown')),
    gpa_condition_type TEXT NOT NULL
        CHECK (
            gpa_condition_type IN (
                'not_applicable',
                'simple_overall_minimum',
                'simple_overall_range',
                'no_gpa_requirement',
                'no_numeric_threshold',
                'qualitative',
                'subject_specific',
                'compound_and',
                'alternative_or',
                'branching',
                'non_admission_numeric',
                'historical_reference',
                'unknown',
                'other'
            )
        ),
    parse_status TEXT NOT NULL
        CHECK (
            parse_status IN (
                'not_applicable',
                'parsed_safe',
                'conditional_review',
                'not_numeric',
                'historical_reference',
                'unknown',
                'unparsed'
            )
        ),
    search_disposition TEXT NOT NULL
        CHECK (
            search_disposition IN (
                'safe_numeric',
                'review_required',
                'not_searchable'
            )
        ),
    source_value_status TEXT NOT NULL
        CHECK (source_value_status IN ('current', 'previous_year_reference')),
    has_subject_condition INTEGER NOT NULL
        CHECK (has_subject_condition IN (0, 1)),
    has_and_condition INTEGER NOT NULL
        CHECK (has_and_condition IN (0, 1)),
    has_or_condition INTEGER NOT NULL
        CHECK (has_or_condition IN (0, 1)),
    has_branch_condition INTEGER NOT NULL
        CHECK (has_branch_condition IN (0, 1)),
    parser_contract_version TEXT NOT NULL
        CHECK (parser_contract_version = '0.1'),

    FOREIGN KEY (admission_rowid)
        REFERENCES admissions (admission_rowid)
        ON UPDATE RESTRICT
        ON DELETE CASCADE,
    CHECK (raw_value IS NULL OR raw_value <> ''),
    CHECK (
        (raw_value IS NULL AND parse_status = 'not_applicable') OR
        (raw_value IS NOT NULL AND parse_status <> 'not_applicable')
    ),
    CHECK (
        gpa_min_tenths IS NULL OR
        (gpa_min_tenths >= 0 AND gpa_min_tenths <= 50)
    ),
    CHECK (
        gpa_max_tenths IS NULL OR
        (gpa_max_tenths >= 0 AND gpa_max_tenths <= 50)
    ),
    CHECK (
        gpa_min_tenths IS NULL OR
        gpa_max_tenths IS NULL OR
        gpa_min_tenths <= gpa_max_tenths
    ),
    CHECK (
        (gpa_min_tenths IS NULL AND gpa_min_inclusive IS NULL) OR
        (gpa_min_tenths IS NOT NULL AND gpa_min_inclusive IS NOT NULL)
    ),
    CHECK (
        (gpa_max_tenths IS NULL AND gpa_max_inclusive IS NULL) OR
        (gpa_max_tenths IS NOT NULL AND gpa_max_inclusive IS NOT NULL)
    ),
    CHECK (
        (
            parse_status = 'parsed_safe' AND
            search_disposition = 'safe_numeric' AND
            source_value_status = 'current' AND
            metric_scope = 'overall' AND
            gpa_scale = 'japanese_5_point' AND
            gpa_condition_type IN (
                'simple_overall_minimum',
                'simple_overall_range'
            ) AND
            gpa_min_tenths IS NOT NULL AND
            has_subject_condition = 0 AND
            has_and_condition = 0 AND
            has_or_condition = 0 AND
            has_branch_condition = 0
        ) OR
        (
            parse_status <> 'parsed_safe' AND
            search_disposition <> 'safe_numeric' AND
            gpa_min_tenths IS NULL AND
            gpa_min_inclusive IS NULL AND
            gpa_max_tenths IS NULL AND
            gpa_max_inclusive IS NULL
        )
    ),
    CHECK (
        gpa_condition_type <> 'simple_overall_minimum' OR
        gpa_max_tenths IS NULL
    ),
    CHECK (
        gpa_condition_type <> 'simple_overall_range' OR
        gpa_max_tenths IS NOT NULL
    )
) STRICT;

-- Optional future structure for fully parsed conditional rules.  Groups are
-- OR alternatives; clauses within one group are AND requirements.  A group is
-- never eligibility-evaluable while its status is not 'complete'.
CREATE TABLE admission_search_gpa_rule_groups (
    gpa_rule_group_id INTEGER PRIMARY KEY,
    admission_rowid INTEGER NOT NULL,
    group_index INTEGER NOT NULL CHECK (group_index >= 1),
    applies_when_raw TEXT,
    group_status TEXT NOT NULL
        CHECK (group_status IN ('complete', 'context_required', 'unparsed')),
    UNIQUE (admission_rowid, group_index),
    FOREIGN KEY (admission_rowid)
        REFERENCES admission_search_gpa (admission_rowid)
        ON UPDATE RESTRICT
        ON DELETE CASCADE
) STRICT;

CREATE TABLE admission_search_gpa_clauses (
    gpa_clause_id INTEGER PRIMARY KEY,
    gpa_rule_group_id INTEGER NOT NULL,
    clause_index INTEGER NOT NULL CHECK (clause_index >= 1),
    metric_scope TEXT NOT NULL
        CHECK (
            metric_scope IN (
                'overall',
                'subject',
                'grade_letter',
                'qualification',
                'non_gpa',
                'unknown'
            )
        ),
    subject_raw TEXT,
    aggregation TEXT NOT NULL
        CHECK (
            aggregation IN (
                'direct',
                'combined_average',
                'each',
                'any_n_of',
                'all',
                'unknown'
            )
        ),
    comparator TEXT NOT NULL
        CHECK (
            comparator IN (
                'gte',
                'gt',
                'lte',
                'lt',
                'between',
                'exact',
                'qualitative',
                'unknown'
            )
        ),
    gpa_min_tenths INTEGER,
    gpa_min REAL GENERATED ALWAYS AS (
        CASE
            WHEN gpa_min_tenths IS NULL THEN NULL
            ELSE gpa_min_tenths / 10.0
        END
    ) VIRTUAL,
    gpa_min_inclusive INTEGER
        CHECK (gpa_min_inclusive IN (0, 1)),
    gpa_max_tenths INTEGER,
    gpa_max REAL GENERATED ALWAYS AS (
        CASE
            WHEN gpa_max_tenths IS NULL THEN NULL
            ELSE gpa_max_tenths / 10.0
        END
    ) VIRTUAL,
    gpa_max_inclusive INTEGER
        CHECK (gpa_max_inclusive IN (0, 1)),
    raw_clause TEXT NOT NULL CHECK (raw_clause <> ''),
    evaluation_status TEXT NOT NULL
        CHECK (
            evaluation_status IN (
                'evaluatable',
                'context_required',
                'qualitative',
                'unparsed'
            )
        ),
    UNIQUE (gpa_rule_group_id, clause_index),
    FOREIGN KEY (gpa_rule_group_id)
        REFERENCES admission_search_gpa_rule_groups (gpa_rule_group_id)
        ON UPDATE RESTRICT
        ON DELETE CASCADE,
    CHECK (
        gpa_min_tenths IS NULL OR
        (gpa_min_tenths >= 0 AND gpa_min_tenths <= 50)
    ),
    CHECK (
        gpa_max_tenths IS NULL OR
        (gpa_max_tenths >= 0 AND gpa_max_tenths <= 50)
    ),
    CHECK (
        gpa_min_tenths IS NULL OR
        gpa_max_tenths IS NULL OR
        gpa_min_tenths <= gpa_max_tenths
    ),
    CHECK (
        (gpa_min_tenths IS NULL AND gpa_min_inclusive IS NULL) OR
        (gpa_min_tenths IS NOT NULL AND gpa_min_inclusive IS NOT NULL)
    ),
    CHECK (
        (gpa_max_tenths IS NULL AND gpa_max_inclusive IS NULL) OR
        (gpa_max_tenths IS NOT NULL AND gpa_max_inclusive IS NOT NULL)
    ),
    CHECK (
        (
            evaluation_status = 'evaluatable' AND
            (gpa_min_tenths IS NOT NULL OR gpa_max_tenths IS NOT NULL)
        ) OR
        (evaluation_status <> 'evaluatable')
    )
) STRICT;

CREATE INDEX idx_admission_search_gpa_safe_min
    ON admission_search_gpa (
        gpa_min_tenths,
        gpa_max_tenths,
        admission_rowid
    )
    WHERE parse_status = 'parsed_safe'
      AND search_disposition = 'safe_numeric';

CREATE INDEX idx_admission_search_gpa_status
    ON admission_search_gpa (
        search_disposition,
        parse_status,
        gpa_condition_type,
        admission_rowid
    );

CREATE INDEX idx_admission_search_gpa_groups_admission
    ON admission_search_gpa_rule_groups (admission_rowid, group_index);

CREATE INDEX idx_admission_search_gpa_clauses_group
    ON admission_search_gpa_clauses (gpa_rule_group_id, clause_index);

CREATE VIEW admission_search_gpa_safe AS
SELECT
    admission_rowid,
    raw_value,
    gpa_min_tenths,
    gpa_min,
    gpa_min_inclusive,
    gpa_max_tenths,
    gpa_max,
    gpa_max_inclusive,
    gpa_scale,
    gpa_condition_type
FROM admission_search_gpa
WHERE parse_status = 'parsed_safe'
  AND search_disposition = 'safe_numeric';
