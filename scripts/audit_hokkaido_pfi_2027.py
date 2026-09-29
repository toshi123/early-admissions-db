#!/usr/bin/env python3
"""Apply the official 2027 Hokkaido private-foreign undergraduate audit.

The source unit list is transcribed from the official R9募集要項 table (p.1-2).
This script is intentionally guarded and idempotent: it adds the 25 verified
units once and updates only the associated audit ledgers and representative
candidate-field pilot row.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATE = "2026-09-28"
PAGE = "https://www.hokudai.ac.jp/admission/faculty/intl-private/"
GUIDE = "https://www.hokudai.ac.jp/admission/shihi_admissionR09.pdf"
CHANGE = "https://www.hokudai.ac.jp/admission/20260813_kaiso_henkou.pdf"
SELECTION = "私費外国人留学生（学部）入試"

# ID, faculty, department, slot, field, EJU subject combination, method key
UNITS = [
    ("LIT", "文学部", "学部一括", "前期日程内数", "人文", "日本語・総合科目・数学（コース1又は2）", "essay"),
    ("EDU", "教育学部", "学部一括", "前期日程内数", "教育", "日本語・総合科目・数学（コース1又は2）", "essay"),
    ("LAW", "法学部", "学部一括", "前期日程内数", "法学", "日本語・総合科目・数学（コース1又は2）", "essay"),
    ("ECON", "経済学部", "学部一括（学科は入学後に決定）", "前期日程内数", "経済学", "日本語・総合科目・数学（コース1又は2）", "essay"),
    ("MATH", "理学部", "数学科", "後期日程内数", "理学", "日本語・数学（コース2）・理科：物理＋化学又は生物", "aptitude"),
    ("PHYS", "理学部", "物理学科", "後期日程内数", "理学", "日本語・数学（コース2）・理科：物理＋化学", "aptitude"),
    ("CHEM", "理学部", "化学科", "後期日程内数", "理学", "日本語・数学（コース2）・理科：物理＋化学", "aptitude"),
    ("BIO", "理学部", "生物科学科（生物学専修分野）", "後期日程内数", "理学", "日本語・数学（コース2）・理科：生物＋物理又は化学", "comprehensive_oral"),
    ("POLY", "理学部", "生物科学科（高分子機能学専修分野）", "後期日程内数", "理学", "日本語・数学（コース2）・理科：物理・化学・生物から2科目", "comprehensive_oral"),
    ("EARTH", "理学部", "地球惑星科学科", "後期日程内数", "理学", "日本語・数学（コース2）・理科：物理・化学・生物から2科目", "comprehensive_oral"),
    ("MED", "医学部", "医学科", "前期日程内数", "医学", "日本語・数学（コース2）・理科：物理＋化学", "essay"),
    ("NURS", "医学部保健学科", "看護学専攻", "前期日程内数", "看護・保健", "日本語・数学（コース2）・理科：物理・化学・生物から2科目", "essay"),
    ("RAD", "医学部保健学科", "放射線技術科学専攻", "前期日程内数", "看護・保健", "日本語・数学（コース2）・理科：物理＋化学又は生物", "essay"),
    ("LAB", "医学部保健学科", "検査技術科学専攻", "前期日程内数", "看護・保健", "日本語・数学（コース2）・理科：化学＋物理又は生物", "essay"),
    ("PT", "医学部保健学科", "理学療法学専攻", "前期日程内数", "看護・保健", "日本語・数学（コース2）・理科：物理・化学・生物から2科目", "essay"),
    ("OT", "医学部保健学科", "作業療法学専攻", "前期日程内数", "看護・保健", "日本語・数学（コース2）・理科：物理・化学・生物から2科目", "essay"),
    ("DENT", "歯学部", "学部一括", "前期日程内数", "歯学", "日本語・数学（コース2）・理科：生物＋物理又は化学", "essay"),
    ("PHARM", "薬学部", "学部一括（学科は入学後に決定）", "後期日程内数", "薬学", "日本語・数学（コース2）・理科：物理・化学・生物から2科目", "comprehensive_oral"),
    ("ENG-APP", "工学部", "応用理工系学科", "後期日程内数", "工学", "日本語・数学（コース2）・理科：物理＋化学又は生物（コース別指定あり）", "interview"),
    ("ENG-INFO", "工学部", "情報エレクトロニクス学科", "後期日程内数", "工学", "日本語・数学（コース2）・理科：物理＋化学又は生物", "interview"),
    ("ENG-MECH", "工学部", "機械知能工学科", "後期日程内数", "工学", "日本語・数学（コース2）・理科：物理＋化学又は生物", "interview"),
    ("ENG-ENV", "工学部", "環境社会工学科", "後期日程内数", "工学", "日本語・数学（コース2）・理科：物理＋化学又は生物", "interview"),
    ("AGR", "農学部", "学部一括（学科は入学後に決定）", "後期日程内数", "農学", "日本語・数学（コース2）・理科：物理・化学・生物から2科目", "essay"),
    ("VET", "獣医学部", "共同獣医学課程", "後期日程内数", "獣医学", "日本語・数学（コース2）・理科：生物＋物理又は化学", "comprehensive"),
    ("FISH", "水産学部", "学部一括（学科は入学後に決定）", "前期日程内数", "水産", "日本語・数学（コース2）・理科：物理・化学・生物から2科目", "comprehensive"),
]

METHODS = {
    "essay": ("課題論文", "課題論文又は課題論文相当の論述試験", "Yes", "No"),
    "aptitude": ("適性試験", "適性試験（数学・理科等。学科別指定）", "No", "No"),
    "comprehensive_oral": ("総合問題", "総合問題。面接には基礎学力確認の筆答・口頭試問を含む。", "No", "Yes"),
    "comprehensive": ("総合問題", "総合問題（募集要項記載の基礎科学・読解・論理等）", "No", "No"),
    "interview": ("面接", "面接で基礎学力・日本語学力・論理的思考力等を評価。", "No", "No"),
}
EJU_MIN = {
    "MED": "日本語（記述含む）385点以上、基礎科目（理科・数学）340点以上",
    "NURS": "日本語（記述含む）340点以上、基礎科目（理科・数学）300点以上",
    "RAD": "日本語（記述含む）340点以上、基礎科目（理科・数学）300点以上",
    "LAB": "日本語（記述含む）340点以上、基礎科目（理科・数学）300点以上",
    "PT": "日本語（記述含む）340点以上、基礎科目（理科・数学）300点以上",
    "OT": "日本語（記述含む）340点以上、基礎科目（理科・数学）300点以上",
    "DENT": "日本語（記述含む）360点以上、基礎科目（理科・数学）300点以上",
    "PHARM": "日本語（記述含む）340点以上、基礎科目（理科・数学）300点以上",
    "AGR": "日本語（記述含む）340点以上、基礎科目（理科・数学）300点以上",
    "VET": "日本語（記述含む）360点以上、基礎科目（理科・数学）320点以上",
}
FOREIGN_ELIGIBILITY = (
    "日本国籍を有せず、日本の永住許可を得ていない者で、外国の12年課程修了（2027-03-31までの修了見込みを含む）、"
    "所定の11年以上課程、認定国際学校課程、IB・Abitur・Baccalaureate・GCE A level・European Baccalaureate、"
    "又は所定の同等資格等のいずれかを満たす者。資格経路により追加条件あり。"
)
EJU_COMMON = (
    "日本留学試験は2024年11月以降（2024-11、2025-06、2025-11、2026-06実施分）を対象とし、"
    "異なる実施回の科目得点は合算不可。"
)
ENGLISH_COMMON = (
    "全募集単位で英語資格・検定成績の提出が必要。文学部はTOEFL-iBT（Home Edition可）、"
    "医学部医学科はTOEFL-iBT（Home Edition可、Test Date score）79以上又はTOEIC L&R 750以上。"
    "その他はTOEFL、TOEIC L&R、国連英検、Cambridge、英検、IELTS又は同等試験の成績証明を提出し、"
    "要項に最低基準点の指定なし。"
)
GRADE = "数値による評定要件なし。最終出身校の成績証明書を選抜資料として使用。"
ACADEMIC_DETAIL = (
    "出願資格経路に応じた最終出身校の卒業・修了証明書及び成績証明書、又はIB等の資格証書・成績評価証明書を提出。"
    "成績関係証明書は学校長又は機関長作成。符号・略字の説明書を添付し、英文・和文以外の書類には公的又は出身校作成の訳文が必要。"
    "日本語教育機関修了者・在籍者は同機関の成績証明書も提出。"
)
DOCS = (
    "入学願書、履歴書、写真票、出願資格証明書及び成績証明書等、日本留学試験成績通知書又は受験票写し、"
    "英語資格・検定成績通知書等、国籍・在留資格確認書類。理学部は志望理由書、獣医学部は自己推薦書を追加。"
    "該当者は日本語教育機関成績証明書も提出。"
)
DEADLINE = "入学手続期間は2026-12-08から2026-12-14 17:00まで。期間内に入学辞退届を提出すれば辞退可能。"


def read_csv(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), [dict(x) for x in reader]


def write_csv(path: Path, header, rows):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def make_row(unit):
    code, faculty, dept, slot, field, eju, method_key = unit
    method_name, method_detail, essay, oral = METHODS[method_key]
    if code == "PHYS":
        oral = "Yes"
    min_score = EJU_MIN.get(code, "日本語（記述含む）270点以上、基礎科目265点以上")
    eng_detail = ENGLISH_COMMON
    return {
        "record_id": f"HU-2027-PFI-{code}", "admission_year": "2027", "institution_type": "国立",
        "university": "北海道大学", "prefecture": "北海道", "academic_field": field,
        "stem_flag": "False" if field in {"人文", "教育", "法学", "経済学"} else "True",
        "faculty_school": faculty, "department": dept, "selection_category": "特別選抜",
        "selection_name": SELECTION, "slot_type": slot,
        "international_baccalaureate_flag": "No", "private_foreign_student_flag": "Yes",
        "returnee_flag": "No", "regional_quota_flag": "No", "adult_selection_flag": "No",
        "capacity": "若干名", "school_recommendation_required": "No", "school_nomination_limit": "",
        "school_nomination_limit_total": "", "school_nomination_limit_rule": "",
        "exclusive_enrollment_status": "併願可",
        "exclusive_enrollment": "合格後に入学辞退届を提出できる。入学確約を出願要件とする記載は確認できない。",
        "exclusive_enrollment_evidence": "入学を辞退する場合は2026年12月14日17時までに入学辞退届を提出",
        "exclusive_enrollment_evidence_page": "21", "exclusive_enrollment_evidence_url": GUIDE,
        "eligibility_graduation": FOREIGN_ELIGIBILITY, "gpa_requirement": GRADE,
        "english_requirement": "外部英語資格・検定試験の成績提出が必要（募集要項所定の試験）",
        "subject_prerequisites": f"日本留学試験の指定科目：{eju}。{min_score}。{EJU_COMMON}",
        "common_test_required": "No", "common_test_usage": "大学入学共通テストを免除。日本留学試験と最終修了学校の成績証明書等を総合評価。",
        "research_activity_level": "not_specified", "research_requirement_required": "No",
        "research_activity_detail": "", "research_requirement_summary": "",
        "academic_record_required": "Yes", "academic_record_type": "最終出身校成績証明書・資格別成績評価証明書等",
        "academic_record_detail": ACADEMIC_DETAIL, "documents_summary": DOCS,
        "selection_process": (f"第1次：出願書類選考。第2次：{method_name}＋面接。日本留学試験・最終出身校成績等を総合評価。共通テスト免除。"
                              if method_key != "interview" else "第1次：出願書類選考。第2次：面接。日本留学試験・最終出身校成績等を総合評価。共通テスト免除。"),
        "selection_document_review": "Yes", "selection_interview": "Yes", "selection_oral_exam": oral,
        "selection_presentation": "No", "selection_essay": essay,
        "selection_written_exam": "No" if method_key == "interview" else "Yes",
        "selection_practical": "No", "selection_group_discussion": "No", "selection_aptitude_test": "Yes" if method_key == "aptitude" else "No",
        "selection_common_test": "No", "interview_detail": "意欲・目的意識・適性・基礎学力等を評価。学科別の指定は募集要項参照。",
        "oral_exam_subjects": "", "oral_exam_detail": "筆答試問・口頭試問の明記がある場合は面接内で基礎学力を確認。" if oral == "Yes" else "",
        "presentation_detail": "", "essay_detail": method_detail if essay == "Yes" else "",
        "written_exam_detail": method_detail if method_key in {"aptitude", "comprehensive", "comprehensive_oral"} else "",
        "selection_method_detail": (f"第1次は出願書類選考。第2次は{method_detail}および面接。選考では日本留学試験と最終修了学校の成績証明書等を総合。{ENGLISH_COMMON}"
                                    if method_key != "interview" else f"第1次は出願書類選考。第2次は{method_detail}。選考では日本留学試験と最終修了学校の成績証明書等を総合。{ENGLISH_COMMON}"),
        "application_start": "2026-09-14", "application_end": "2026-09-18",
        "web_registration_period": "2026-09-07 10:00〜2026-09-17 17:00（検定料支払期間）",
        "first_stage_result_date": "2026-10-27", "second_stage_start": "2026-11-15", "second_stage_end": "2026-11-15",
        "final_result_date": "2026-12-08", "source_status": "2027年度公式募集要項精査済",
        "detail_completeness": "complete（2027年度公式募集要項で募集単位・出願資格・提出書類・選抜方法・日程を確認）",
        "verification_grade": "A", "verified_on": DATE, "source_url": PAGE, "schedule_url": GUIDE, "guideline_url": GUIDE,
        "notes": (f"2026-09-28再監査。募集人員表（要項p.1-2）の学部・学科等別25単位をそのまま収録。"
                  f"コース下位記載を独立単位とせず、工学部4学科単位、農・薬・水産は学部単位。全行のcapacityは若干名。"
                  f"private_foreign_student_flag=Yes。他4フラグは独立した募集枠でないためNo。IB資格経路があることのみではIB選抜にしない。"
                  f"{DEADLINE} 改組告知は奨学支援担当部署名のみ変更（{CHANGE}）。")
        , "information_year": "2027", "publication_status": "2027年度公式募集要項公開済",
        "fallback_previous_year": "No", "current_year_release_expected": "公表済",
        "previous_year_source_url": "", "fallback_note": "",
    }


def main():
    master_path = ROOT / "data/canonical/kokkoritsu/master.csv"
    header, rows = read_csv(master_path)
    hu = [r for r in rows if r["university"] == "北海道大学"]
    new_rows = [make_row(u) for u in UNITS]
    if len(new_rows) != 25 or len({r['record_id'] for r in new_rows}) != 25:
        raise SystemExit("Unit definition count or record IDs are not unique")
    if set(header) != set(new_rows[0]):
        raise SystemExit("Master columns differ from generated row fields")
    current_by_id = {r["record_id"]: r for r in hu}
    expected_ids = {r["record_id"] for r in new_rows}
    existing_pfi = {r["record_id"] for r in hu if r["private_foreign_student_flag"] == "Yes"}
    if len(hu) == 49 and not existing_pfi:
        rows.extend(new_rows)
    elif len(hu) == 74 and existing_pfi == expected_ids:
        for generated in new_rows:
            current_by_id[generated["record_id"]].update(generated)
    else:
        raise SystemExit(f"Unexpected Hokkaido baseline: rows={len(hu)} PFI={len(existing_pfi)}")
    write_csv(master_path, header, rows)

    # Canonical coverage is a derived count from Master and must stay exact.
    path = ROOT / "data/canonical/kokkoritsu/coverage.csv"
    h, cov = read_csv(path)
    c = next(r for r in cov if r["university"] == "北海道大学")
    c.update({"research_status": "Master反映済・追加項目再監査済", "master_rows": "74",
              "current_year_status": "2027年度私費外国人留学生（学部）入試25募集単位を追加。既存選抜を含むMaster74行を再監査済",
              "fallback_status": "不要（2027年度公式情報あり）", "checked_on": DATE,
              "official_source_url": PAGE,
              "notes": "2027年度私費外国人留学生（学部）入試募集人員表・募集要項を確認し、25実出願単位を追加。工学部は4学科単位、農・薬・水産は学部単位。募集人員はいずれも若干名。提出書類、出願資格、EJU、英語、成績資料、選考方法、日程・入学手続を反映。改組告知は奨学支援部署名の訂正のみ。"})
    write_csv(path, h, cov)

    path = ROOT / "data/operations/coverage_reaudit_2027.csv"
    h, rows = read_csv(path)
    op = next(r for r in rows if r["source_dataset"] == "kokkoritsu" and r["university"] == "北海道大学")
    op.update({"reaudit_status": "再監査済", "official_system_checked": "実施済", "capacity_table_checked": "実施済",
               "schedule_checked": "実施済", "guideline_index_checked": "実施済", "master_compared": "実施済",
               "missing_candidate_count": "0", "ambiguous_candidate_count": "0", "obsolete_candidate_count": "0",
               "update_queue_open_count": "0", "last_audited_on": DATE,
               "notes": "公式入試体系・募集人員表・日程・募集要項一覧を確認し、Master既存49行と照合。私費外国人留学生（学部）入試25単位を追加。Kei-Netは照合に使用せず、公式資料を一次根拠とした。"})
    write_csv(path, h, rows)

    path = ROOT / "data/operations/update_queue.csv"
    h, rows = read_csv(path)
    if not any(r["queue_id"] == "UQ-2027-0045" for r in rows):
        rows.append({"queue_id": "UQ-2027-0045", "institution_type": "国立", "university": "北海道大学",
                     "faculty_school": "全学部", "selection_name": SELECTION, "document_type": "募集要項",
                     "publication_status": "公開済", "release_expected_text": "2026年5月29日掲載",
                     "release_expected_from": "2026-05-29", "release_expected_to": "2026-05-29",
                     "release_schedule_url": PAGE, "last_checked_on": DATE, "next_check_on": "",
                     "actual_release_on": "2026-05-29", "action_status": "完了",
                     "related_record_id": "HU-2027-PFI-LIT",
                     "notes": "募集要項・募集人員表・8月13日部署名変更告知を照合。25募集単位をMasterへ反映し、資格・要件・提出書類・方法・日程・手続期限を精査済。"})
    write_csv(path, h, rows)

    path = ROOT / "data/operations/canonical_corrections_2027.jsonl"
    records = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x]
    cid = "CC-2027-0009"
    if not any(x.get("correction_id") == cid for x in records):
        records.append({"correction_id": cid, "dataset": "kokkoritsu", "university": "北海道大学",
                        "detected_on": DATE, "status": "applied_complete",
                        "reason": "公式募集人員表との照合で私費外国人留学生（学部）入試25募集単位がMaster未収録と確認された。",
                        "existing_master_rows": 49,
                        "missing_selection_groups": [{"selection_name": SELECTION, "confirmed_units": 25,
                                                      "grain": "公式募集人員表の学部・学科等別。理学の専修分野・医学保健専攻を分け、工学部は4学科単位、農・薬・水産は学部単位。",
                                                      "apply_status": "applied_complete", "update_queue_id": "UQ-2027-0045"}],
                        "confirmed_missing_units_total": 25, "applied_master_rows": 25,
                        "current_university_master_rows": 74, "official_source": "2027年度私費外国人留学生（学部）入試募集要項・大学公式入試ページ",
                        "official_url": GUIDE, "update_queue_id": "UQ-2027-0045",
                        "audit_note": ("募集単位25、各若干名。出願資格、EJU科目・得点、英語提出条件、資格別成績証明書、選考方法、出願・合格発表日、入学手続期限を反映。"
                                       "フラグ判定：IB=No（IBは出願資格経路で独立選抜枠でない）、私費外国人=Yes、帰国生=No（別制度）、地域枠=No、社会人=No。"
                                       "入学辞退届が期限内に提出可能なため専願とはせず併願可。既存49行とID・重複照合済。"
                                       f"組織改組告知（部署名のみ変更）: {CHANGE}")})
        path.write_text("".join(json.dumps(x, ensure_ascii=False, separators=(",", ":")) + "\n" for x in records), encoding="utf-8")

    path = ROOT / "data/operations/candidate_fields_pilot_2027.csv"
    h, rows = read_csv(path)
    existing = next((r for r in rows if r["record_id"] == "HU-2027-PFI-LIT"), None)
    pilot = {"source_dataset": "kokkoritsu", "record_id": "HU-2027-PFI-LIT", "university": "北海道大学",
             "faculty_school": "文学部", "department": "学部一括", "selection_name": SELECTION,
             "slot_type": "前期日程内数", "enrollment_procedure_deadline": "2026-12-14 17:00",
             "enrollment_procedure_detail": "2026-12-08から12-14 17:00まで。辞退の場合も期限までに入学辞退届を提出。",
             "graduation_eligibility_status": "既卒可", "years_since_graduation_max": "",
             "graduation_eligibility_detail": FOREIGN_ELIGIBILITY,
             "regional_requirement_status": "No", "regional_requirement_detail": "募集要項に居住地・出身高校所在地等による地域枠要件なし。",
             "gender_requirement": "制限なし", "gender_requirement_detail": "当該入試に性別による出願条件の記載なし。",
             "guideline_url": GUIDE, "reviewed_on": DATE, "pilot_status": "pilot",
             "notes": "北海道大学私費外国人留学生入試の代表行。卒業経路は複数のため年数上限は推定せず空欄。"}
    if existing:
        rows[rows.index(existing)] = pilot
    else:
        rows.append(pilot)
    write_csv(path, h, rows)
    print("Applied Hokkaido PFI: 25 units; total Hokkaido Master rows 74")


if __name__ == "__main__":
    main()
