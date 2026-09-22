-- Academic-field exact-crosswalk derived search layer v0.1.
-- The builder loads the taxonomy lookup before derived parent/child rows.

CREATE TABLE academic_field_taxonomy (
    group_code TEXT PRIMARY KEY,
    display_label TEXT NOT NULL CHECK (display_label <> ''),
    description TEXT NOT NULL CHECK (description <> ''),
    display_order INTEGER NOT NULL UNIQUE CHECK (display_order >= 1),
    taxonomy_version TEXT NOT NULL CHECK (taxonomy_version = '0.1')
) STRICT;

CREATE TABLE admission_search_academic_fields (
    admission_rowid INTEGER PRIMARY KEY
        REFERENCES admissions(admission_rowid) ON DELETE CASCADE,
    raw_value TEXT,
    mapping_status TEXT NOT NULL
        CHECK (mapping_status IN (
            'single',
            'multi',
            'review_required',
            'unmapped',
            'not_applicable'
        )),
    mapping_contract_version TEXT NOT NULL
        CHECK (mapping_contract_version = '0.2'),
    review_note TEXT,
    CHECK (
        (raw_value IS NULL AND mapping_status = 'not_applicable')
        OR
        (raw_value IS NOT NULL AND mapping_status <> 'not_applicable')
    )
) STRICT;

CREATE TABLE admission_search_academic_field_groups (
    admission_rowid INTEGER NOT NULL
        REFERENCES admission_search_academic_fields(admission_rowid)
        ON DELETE CASCADE,
    group_code TEXT NOT NULL
        REFERENCES academic_field_taxonomy(group_code)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT,
    group_order INTEGER NOT NULL CHECK (group_order >= 1),
    mapping_basis TEXT NOT NULL DEFAULT 'exact_crosswalk'
        CHECK (mapping_basis = 'exact_crosswalk'),
    PRIMARY KEY (admission_rowid, group_code),
    UNIQUE (admission_rowid, group_order)
) STRICT;

CREATE INDEX idx_academic_field_parent_status
    ON admission_search_academic_fields(mapping_status, admission_rowid);

CREATE INDEX idx_academic_field_group_lookup
    ON admission_search_academic_field_groups(group_code, admission_rowid);
