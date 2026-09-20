from pathlib import Path
import unittest

from early_admissions.english_requirement import EnglishRequirementCrosswalk


ROOT = Path(__file__).resolve().parents[1]


class EnglishRequirementTests(unittest.TestCase):
    def setUp(self) -> None:
        self.crosswalk = EnglishRequirementCrosswalk.load(
            ROOT / "schema/english_requirement/english_requirement_crosswalk_v0_1.csv"
        )

    def test_exact_crosswalk_is_fail_closed(self) -> None:
        required = self.crosswalk.classify("英検準1級以上、TOEFL iBT所定基準、TOEIC L&R 600点以上等の英語資格要件")
        self.assertEqual(required.requirement_status, "required")
        self.assertEqual(required.search_disposition, "safe_exact")
        missing = self.crosswalk.classify(None)
        self.assertEqual(missing.requirement_status, "unknown")
        self.assertEqual(missing.parse_status, "missing")
        novel = self.crosswalk.classify("将来追加された未監査の表現")
        self.assertEqual(novel.requirement_status, "unmapped")
        self.assertEqual(novel.search_disposition, "review_required")

    def test_crosswalk_snapshot_is_complete_and_unique(self) -> None:
        self.assertEqual(len(self.crosswalk), 177)
