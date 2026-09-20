CREATE TABLE prefecture_taxonomy (
    prefecture_code TEXT PRIMARY KEY,
    prefecture_label TEXT NOT NULL UNIQUE,
    region TEXT NOT NULL,
    display_order INTEGER NOT NULL UNIQUE CHECK(display_order BETWEEN 1 AND 47),
    taxonomy_version TEXT NOT NULL CHECK(taxonomy_version='0.1')
) STRICT;
CREATE TABLE admission_search_prefectures (
    admission_rowid INTEGER PRIMARY KEY REFERENCES admissions(admission_rowid) ON DELETE CASCADE,
    raw_value TEXT,
    mapping_status TEXT NOT NULL CHECK(mapping_status IN ('single','multi','review_required','unmapped','not_applicable')),
    mapping_contract_version TEXT NOT NULL CHECK(mapping_contract_version='0.1'),
    review_note TEXT,
    CHECK((raw_value IS NULL AND mapping_status='not_applicable') OR (raw_value IS NOT NULL AND mapping_status<>'not_applicable'))
) STRICT;
CREATE TABLE admission_search_prefecture_memberships (
    admission_rowid INTEGER NOT NULL REFERENCES admission_search_prefectures(admission_rowid) ON DELETE CASCADE,
    prefecture_code TEXT NOT NULL REFERENCES prefecture_taxonomy(prefecture_code),
    prefecture_label TEXT NOT NULL,
    membership_order INTEGER NOT NULL CHECK(membership_order>=1),
    mapping_basis TEXT NOT NULL CHECK(mapping_basis='exact_crosswalk'),
    PRIMARY KEY(admission_rowid,prefecture_code), UNIQUE(admission_rowid,membership_order)
) STRICT;
CREATE INDEX idx_prefecture_membership_lookup ON admission_search_prefecture_memberships(prefecture_label,admission_rowid);
CREATE INDEX idx_prefecture_parent_status ON admission_search_prefectures(mapping_status,admission_rowid);
