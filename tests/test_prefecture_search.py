from pathlib import Path
import unittest

from early_admissions.prefecture_search import PrefectureCrosswalk, PrefectureTaxonomy
from early_admissions.structured_search import SearchCriteria, search_database

ROOT=Path(__file__).resolve().parents[1]

class PrefectureContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.taxonomy=PrefectureTaxonomy.load(ROOT/"schema/prefecture/prefecture_taxonomy_v0_1.csv")
        cls.crosswalk=PrefectureCrosswalk.load(ROOT/"schema/prefecture/prefecture_crosswalk_v0_1.csv",cls.taxonomy)
    def test_frozen_taxonomy_and_crosswalk(self):
        self.assertEqual(len(self.taxonomy.items),47); self.assertEqual(len(self.crosswalk),48)
        self.assertEqual(self.crosswalk.lookup("東京都").mapping_status,"single")
        multi=self.crosswalk.lookup("東京都・埼玉県")
        self.assertEqual((multi.mapping_status,multi.codes),("multi",("11","13")))
    def test_future_unknown_fails_closed(self):
        mapped=self.crosswalk.lookup("東京都/埼玉県")
        self.assertEqual(mapped.mapping_status,"unmapped"); self.assertEqual(mapped.codes,())

class CurrentPrefectureSearchRegression(unittest.TestCase):
    def test_membership_qa(self):
        db=ROOT/"data/derived/sqlite/v0_2_candidate/early_admissions_2027.sqlite"
        self.assertEqual(search_database(db,SearchCriteria(),limit=0).summary.total_matched_rows,6592)
        self.assertEqual(search_database(db,SearchCriteria(prefecture=("東京都",)),limit=0).summary.total_matched_rows,1415)
        self.assertEqual(search_database(db,SearchCriteria(prefecture_membership=("東京都",)),limit=0).summary.total_matched_rows,1442)
        self.assertEqual(search_database(db,SearchCriteria(prefecture_membership=("東京都","埼玉県")),limit=0).summary.total_matched_rows,1821)
        self.assertEqual(search_database(db,SearchCriteria(prefecture_membership=("東京都",),academic_field_group=("engineering",)),limit=0).summary.total_matched_rows,397)
        self.assertEqual(search_database(db,SearchCriteria(prefecture_membership=("東京都",),gpa_tenths=38,gpa_mode="safe"),limit=0).summary.total_matched_rows,89)
