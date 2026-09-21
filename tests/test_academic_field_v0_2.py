from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from early_admissions.academic_field_v0_2 import (
    CONTEXT_HEADER,
    RAW_HEADER,
    FreezePaths,
    sha256,
    validate_and_summarize,
)


ROOT = Path(__file__).resolve().parents[1]
PATHS = FreezePaths(ROOT)


def grouped_memberships(
    path: Path, header: tuple[str, ...], key_columns: tuple[str, ...]
) -> dict[tuple[str, ...], tuple[tuple[str, str], ...]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != header:
            raise AssertionError(f"unexpected header: {reader.fieldnames!r}")
        grouped: dict[tuple[str, ...], list[tuple[str, str]]] = {}
        for row in reader:
            key = tuple(row[column] for column in key_columns)
            grouped.setdefault(key, [])
            if row["group_code"]:
                grouped[key].append((row["group_code"], row["subcategory_code"]))
    return {key: tuple(values) for key, values in grouped.items()}


class AcademicFieldV02FreezeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.summary = validate_and_summarize(ROOT)
        cls.raw = grouped_memberships(PATHS.raw, RAW_HEADER, ("raw_value",))
        cls.context = grouped_memberships(
            PATHS.context,
            CONTEXT_HEADER,
            (
                "source_dataset",
                "university",
                "faculty_school",
                "department",
                "academic_field",
            ),
        )

    def test_snapshot_counts_and_coverage(self) -> None:
        self.assertEqual(self.summary["input_rows"], {"kokkoritsu": 3668, "shidai": 2253})
        self.assertEqual(self.summary["total_admissions"], 5921)
        self.assertEqual(self.summary["academic_field_null"], 0)
        self.assertEqual(self.summary["raw_distinct"], 448)
        self.assertEqual(self.summary["program_context_distinct"], 2667)
        self.assertEqual(self.summary["broad_taxonomy_count"], 30)
        self.assertEqual(self.summary["subcategory_taxonomy_count"], 89)
        self.assertEqual(self.summary["raw_crosswalk_rows"], 796)
        self.assertEqual(self.summary["raw_crosswalk_distinct"], 448)
        self.assertEqual(self.summary["context_crosswalk_rows"], 824)
        self.assertEqual(self.summary["context_crosswalk_distinct"], 718)
        self.assertEqual(self.summary["raw_only_mapping_admissions"], 4443)
        self.assertEqual(self.summary["context_mapping_admissions"], 1478)
        self.assertEqual(self.summary["context_mapped_admissions"], 1467)
        self.assertEqual(self.summary["broad_coverage_admissions"], 5910)
        self.assertEqual(self.summary["subcategory_coverage_admissions"], 5027)
        self.assertEqual(self.summary["broad_review_required"], 11)
        self.assertEqual(self.summary["subcategory_review_required"], 11)
        self.assertEqual(self.summary["unmapped"], 0)

    def test_high_risk_contained_tokens_and_aviation_fail_closed(self) -> None:
        self.assertEqual(
            self.raw[("理学療法",)],
            (("nursing_health", "physical_therapy"),),
        )
        self.assertEqual(
            self.raw[("言語聴覚",)],
            (("nursing_health", "speech_hearing"),),
        )
        self.assertEqual(
            self.raw[("獣医学",)],
            (("veterinary", "veterinary_medicine"),),
        )
        self.assertEqual(self.raw[("航空・パイロット",)], ())
        self.assertIn(("engineering", "aerospace"), self.raw[("航空工学・ドローン",)])
        self.assertNotIn(("engineering", "aerospace"), self.raw[("航空・整備",)])

    def test_ambiguous_values_use_exact_context_or_remain_review_required(self) -> None:
        self.assertEqual(
            self.raw[("国際",)], (("international_regional", ""),)
        )
        self.assertEqual(self.raw[("人間科学",)], ())
        self.assertEqual(self.raw[("地域デザイン",)], ())
        self.assertEqual(
            self.context[
                (
                    "kokkoritsu",
                    "宇都宮大学",
                    "地域デザイン科学部",
                    "コミュニティデザイン学科",
                    "地域デザイン",
                )
            ],
            (("sociology_community", "community_regional_society"),),
        )
        self.assertEqual(
            self.context[
                (
                    "kokkoritsu",
                    "金沢大学",
                    "融合学域",
                    "観光デザイン学類",
                    "地域デザイン",
                )
            ],
            (("tourism_hospitality", ""),),
        )
        self.assertEqual(
            self.context[
                (
                    "kokkoritsu",
                    "宇都宮大学",
                    "国際学部",
                    "国際学科",
                    "国際",
                )
            ],
            (("international_regional", "international_studies"),),
        )

    def test_frozen_csv_hashes(self) -> None:
        self.assertEqual(
            sha256(PATHS.broad),
            "ba33e98fa58196a3b530b26ce47d036073bdbf929a6fd16636e2ff58afe72ebd",
        )
        self.assertEqual(
            sha256(PATHS.subcategory),
            "9813972ec7698cd923fbbfb9bbee16bff7af12b371f23f5e733f6d391b92576e",
        )
        self.assertEqual(
            sha256(PATHS.raw),
            "bf8213c7fbe09877ed0ffd4701e985e3aad724e0cc519f6e1ba18ed53b8b83aa",
        )
        self.assertEqual(
            sha256(PATHS.context),
            "d6a80cc20c50e225f36eb96c0f51e8df367ffe3b2205bc1fbe5b83d5315eabf1",
        )
        self.assertEqual(
            sha256(PATHS.compatibility),
            "55d3cbeebb0af7d6bcab6bb5b975616413ff8f5591cf3cab03089559913f92d7",
        )

    def test_two_independent_rebuilds_are_byte_identical(self) -> None:
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            first_path = Path(first)
            second_path = Path(second)
            validate_and_summarize(ROOT, first_path)
            validate_and_summarize(ROOT, second_path)
            for source in (
                PATHS.broad,
                PATHS.subcategory,
                PATHS.raw,
                PATHS.context,
                PATHS.compatibility,
            ):
                self.assertEqual(
                    (first_path / source.name).read_bytes(),
                    (second_path / source.name).read_bytes(),
                )
                self.assertEqual(
                    source.read_bytes(), (first_path / source.name).read_bytes()
                )


if __name__ == "__main__":
    unittest.main()
