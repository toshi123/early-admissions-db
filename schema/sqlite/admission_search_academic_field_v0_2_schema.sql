-- Academic-field exact raw/context derived search layer v0.2.
-- This is parallel to, and does not replace, the frozen v0.1 layer.

CREATE TABLE academic_field_v2_broad_taxonomy (
    group_code TEXT PRIMARY KEY,
    display_label_ja TEXT NOT NULL CHECK (display_label_ja <> ''),
    ui_section TEXT NOT NULL CHECK (ui_section <> ''),
    display_order INTEGER NOT NULL CHECK (display_order >= 1),
    description TEXT NOT NULL CHECK (description <> ''),
    status TEXT NOT NULL CHECK (status = 'active'),
    taxonomy_version TEXT NOT NULL CHECK (taxonomy_version = '0.2'),
    UNIQUE (ui_section, display_order)
) STRICT;

CREATE TABLE academic_field_v2_subcategory_taxonomy (
    subcategory_code TEXT PRIMARY KEY,
    display_label_ja TEXT NOT NULL CHECK (display_label_ja <> ''),
    parent_group_code TEXT NOT NULL
        REFERENCES academic_field_v2_broad_taxonomy(group_code)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT,
    display_order INTEGER NOT NULL CHECK (display_order >= 1),
    description TEXT NOT NULL CHECK (description <> ''),
    ui_status TEXT NOT NULL
        CHECK (ui_status IN ('primary', 'secondary', 'hidden')),
    taxonomy_version TEXT NOT NULL CHECK (taxonomy_version = '0.2'),
    UNIQUE (parent_group_code, display_order),
    UNIQUE (subcategory_code, parent_group_code)
) STRICT;

CREATE TABLE admission_search_academic_fields_v2 (
    admission_rowid INTEGER PRIMARY KEY
        REFERENCES admissions(admission_rowid) ON DELETE CASCADE,
    raw_value TEXT,
    broad_mapping_status TEXT NOT NULL
        CHECK (broad_mapping_status IN (
            'single', 'multi', 'review_required', 'unmapped', 'not_applicable'
        )),
    subcategory_mapping_status TEXT NOT NULL
        CHECK (subcategory_mapping_status IN (
            'single', 'multi', 'none', 'review_required', 'unmapped',
            'not_applicable'
        )),
    context_mapping_consulted INTEGER NOT NULL
        CHECK (context_mapping_consulted IN (0, 1)),
    context_mapping_effect TEXT NOT NULL
        CHECK (context_mapping_effect IN ('none', 'additive', 'authoritative')),
    mapping_contract_version TEXT NOT NULL
        CHECK (mapping_contract_version = '0.2'),
    taxonomy_version TEXT NOT NULL CHECK (taxonomy_version = '0.2'),
    review_note TEXT,
    CHECK (
        (raw_value IS NULL
         AND broad_mapping_status = 'not_applicable'
         AND subcategory_mapping_status = 'not_applicable')
        OR
        (raw_value IS NOT NULL
         AND broad_mapping_status <> 'not_applicable'
         AND subcategory_mapping_status <> 'not_applicable')
    ),
    CHECK (
        context_mapping_effect = 'none' OR context_mapping_consulted = 1
    )
) STRICT;

CREATE TABLE admission_search_academic_field_broad_memberships_v2 (
    admission_rowid INTEGER NOT NULL
        REFERENCES admission_search_academic_fields_v2(admission_rowid)
        ON DELETE CASCADE,
    group_code TEXT NOT NULL
        REFERENCES academic_field_v2_broad_taxonomy(group_code)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT,
    membership_order INTEGER NOT NULL CHECK (membership_order >= 1),
    mapping_basis TEXT NOT NULL
        CHECK (mapping_basis IN (
            'raw_exact', 'context_exact', 'raw_and_context'
        )),
    PRIMARY KEY (admission_rowid, group_code),
    UNIQUE (admission_rowid, membership_order)
) STRICT;

CREATE TABLE admission_search_academic_field_subcategory_memberships_v2 (
    admission_rowid INTEGER NOT NULL,
    subcategory_code TEXT NOT NULL,
    parent_group_code TEXT NOT NULL,
    membership_order INTEGER NOT NULL CHECK (membership_order >= 1),
    mapping_basis TEXT NOT NULL
        CHECK (mapping_basis IN (
            'raw_exact', 'context_exact', 'raw_and_context'
        )),
    PRIMARY KEY (admission_rowid, subcategory_code),
    UNIQUE (admission_rowid, membership_order),
    FOREIGN KEY (admission_rowid)
        REFERENCES admission_search_academic_fields_v2(admission_rowid)
        ON DELETE CASCADE,
    FOREIGN KEY (subcategory_code, parent_group_code)
        REFERENCES academic_field_v2_subcategory_taxonomy(
            subcategory_code, parent_group_code
        )
        ON UPDATE RESTRICT
        ON DELETE RESTRICT,
    FOREIGN KEY (admission_rowid, parent_group_code)
        REFERENCES admission_search_academic_field_broad_memberships_v2(
            admission_rowid, group_code
        )
        ON UPDATE RESTRICT
        ON DELETE RESTRICT
) STRICT;

CREATE INDEX idx_academic_field_v2_broad_lookup
    ON admission_search_academic_field_broad_memberships_v2(
        group_code, admission_rowid
    );

CREATE INDEX idx_academic_field_v2_subcategory_lookup
    ON admission_search_academic_field_subcategory_memberships_v2(
        subcategory_code, admission_rowid
    );

CREATE INDEX idx_academic_field_v2_parent_broad_status
    ON admission_search_academic_fields_v2(
        broad_mapping_status, admission_rowid
    );

CREATE INDEX idx_academic_field_v2_parent_subcategory_status
    ON admission_search_academic_fields_v2(
        subcategory_mapping_status, admission_rowid
    );
