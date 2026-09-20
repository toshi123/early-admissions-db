from __future__ import annotations

import csv
import hashlib
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from early_admissions.academic_field import (
    AcademicFieldContractError,
    AcademicFieldCrosswalk,
    AcademicFieldTaxonomy,
)

from tests.test_validator import REPO_ROOT


TAXONOMY_PATH = (
    REPO_ROOT / "schema/academic_field/academic_field_taxonomy_v0_1.csv"
)
CROSSWALK_PATH = (
    REPO_ROOT / "schema/academic_field/academic_field_crosswalk_v0_1.csv"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class AcademicFieldCrosswalkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.taxonomy = AcademicFieldTaxonomy.load(TAXONOMY_PATH)
        cls.crosswalk = AcademicFieldCrosswalk.load(
            CROSSWALK_PATH, cls.taxonomy
        )

    def test_freeze_regression_and_hashes(self) -> None:
        self.assertEqual(len(self.taxonomy), 19)
        self.assertEqual(len(self.crosswalk), 448)
        self.assertEqual(
            Counter(mapping.mapping_status for mapping in self.crosswalk),
            {"single": 199, "multi": 245, "review_required": 4},
        )
        self.assertEqual(
            sha256(CROSSWALK_PATH),
            "8f2c8034395cf7ceebb9675b966d34b638b94cb50569bb90bc426091bac4e762",
        )
        self.assertEqual(
            sha256(TAXONOMY_PATH),
            "f1f52d0282618eb5b22d3c420010718eb30f4ec14ad889dd574f218a5743a9f2",
        )

    def test_representative_exact_multi_and_single_mappings(self) -> None:
        expected = {
            "理工・情報": (
                "natural_sciences",
                "engineering",
                "information",
            ),
            "農学・生命": ("agriculture_fisheries", "life_sciences"),
            "人文・社会": ("humanities", "social_sciences"),
            "デザイン・データ科学": ("information", "arts_design"),
            "スポーツ工学": ("engineering", "sports"),
            "アグリビジネス": (
                "agriculture_fisheries",
                "social_sciences",
            ),
            "数理科学・統計": ("natural_sciences", "information"),
            "医歯薬": ("medicine", "dentistry", "pharmacy"),
            "理学療法": ("nursing_health_welfare",),
            "獣医学": ("veterinary",),
        }
        for raw_value, groups in expected.items():
            with self.subTest(raw_value=raw_value):
                self.assertEqual(
                    self.crosswalk.lookup(raw_value).group_codes, groups
                )

    def test_review_required_values_have_no_groups(self) -> None:
        expected = {"人間科学", "国際", "地域デザイン", "航空・パイロット"}
        actual = {
            mapping.raw_value
            for mapping in self.crosswalk
            if mapping.mapping_status == "review_required"
        }
        self.assertEqual(actual, expected)
        for raw_value in expected:
            mapping = self.crosswalk.lookup(raw_value)
            self.assertEqual(mapping.group_codes, ())
            self.assertTrue(mapping.review_note)

    def test_unknown_and_substring_like_values_fail_closed_without_trim(self) -> None:
        for raw_value in ("理学療法X", "工学 ", "国際観光unknown"):
            with self.subTest(raw_value=raw_value):
                mapping = self.crosswalk.lookup(raw_value)
                self.assertEqual(mapping.mapping_status, "unmapped")
                self.assertEqual(mapping.group_codes, ())
        null_mapping = self.crosswalk.lookup(None)
        self.assertEqual(null_mapping.mapping_status, "not_applicable")
        self.assertEqual(null_mapping.group_codes, ())

    def test_current_unified_raw_vocabulary_equals_freeze(self) -> None:
        with (
            REPO_ROOT / "data/canonical/unified/master.csv"
        ).open("r", encoding="utf-8", newline="") as handle:
            values = {row["academic_field"] for row in csv.DictReader(handle)}
        self.assertNotIn("", values)
        self.assertEqual(values, set(self.crosswalk.by_raw_value))

    def test_invalid_group_code_is_rejected_by_crosswalk_loader(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            corrupted = Path(directory) / "crosswalk.csv"
            raw = CROSSWALK_PATH.read_text(encoding="utf-8")
            corrupted.write_text(
                raw.replace(",agriculture_fisheries,", ",invalid_group,", 1),
                encoding="utf-8",
                newline="",
            )
            with self.assertRaisesRegex(AcademicFieldContractError, "Unknown group"):
                AcademicFieldCrosswalk.load(corrupted, self.taxonomy)


if __name__ == "__main__":
    unittest.main()
