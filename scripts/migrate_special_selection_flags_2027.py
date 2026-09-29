#!/usr/bin/env python3
"""One-shot 2027 migration: formal special-selection flags + Tokyo Gakugei units."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FLAGS = [
    "international_baccalaureate_flag",
    "private_foreign_student_flag",
    "returnee_flag",
    "regional_quota_flag",
]

KOK_MASTER = ROOT / "data/canonical/kokkoritsu/master.csv"
SHI_MASTER = ROOT / "data/canonical/shidai/master.csv"
KOK_COVERAGE = ROOT / "data/canonical/kokkoritsu/coverage.csv"
OPS_COVERAGE = ROOT / "data/operations/coverage_reaudit_2027.csv"
CORRECTIONS = ROOT / "data/operations/canonical_corrections_2027.jsonl"

def read_csv(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        return list(reader.fieldnames or []), [dict(r) for r in reader]

def write_csv(path: Path, header: list[str], rows: list[dict[str, str]]):
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=header, lineterminator="\n", extrasaction="raise")
        w.writeheader()
        w.writerows(rows)

def ensure_header(header: list[str]) -> list[str]:
    if all(f in header for f in FLAGS):
        return header
    pos = header.index("slot_type") + 1
    return header[:pos] + FLAGS + header[pos:]

def flag_values(row: dict[str, str]) -> dict[str, str]:
    cat = row.get("selection_category", "")
    name = row.get("selection_name", "")
    slot = row.get("slot_type", "")
    all_text = f"{cat} {name} {slot}"

    ib = bool(re.search(r"国際バカロレア", all_text))
    ib = ib or bool(re.search(r"IBDP利用|IB方式|IB選抜|IB入試", slot))
    if re.search(r"\bIB\b", name) and "SAT/ACT方式" not in slot:
        ib = True
    if "SAT/ACT・IB入試" in name and "SAT/ACT方式" in slot:
        ib = False
    if re.search(r"IB.*内数|内数.*IB", slot):
        ib = False

    foreign = "私費外国人留学生" in all_text
    returnee = bool(re.search(r"帰国生|帰国子女|帰国生徒|帰国学生|帰国者|帰国", all_text))

    regional = bool(re.search(
        r"地域枠|地域特別枠|地域推薦|県内募集枠|県外募集枠|県内枠|県外枠|県内推薦|県外推薦",
        all_text,
    ))
    if re.search(r"一般枠.*(?:地域枠|地域特別枠).*内数", slot):
        regional = False

    return {
        "international_baccalaureate_flag": "Yes" if ib else "No",
        "private_foreign_student_flag": "Yes" if foreign else "No",
        "returnee_flag": "Yes" if returnee else "No",
        "regional_quota_flag": "Yes" if regional else "No",
    }

def migrate_existing(path: Path):
    old_header, rows = read_csv(path)
    header = ensure_header(old_header)
    for row in rows:
        row.update(flag_values(row))
        for key in header:
            row.setdefault(key, "")
    return header, rows

COURSES = [
    ("A","JPN","国語コース",False,True),("A","SOC","社会コース",False,True),
    ("A","MATH","数学コース",True,True),("A","SCI","理科コース",True,True),
    ("A","MUSIC","音楽コース",False,False),("A","ART","美術コース",False,True),
    ("A","PE","保健体育コース",False,True),("A","HOME","家庭コース",False,True),
    ("A","ENG","英語コース",False,True),
    ("A","SCH","現代教育実践コース（学校教育プログラム）",False,True),
    ("A","PSY","現代教育実践コース（学校心理プログラム）",False,True),
    ("A","INTL","現代教育実践コース（国際教育プログラム）",False,True),
    ("A","ENV","現代教育実践コース（環境教育プログラム）",False,False),
    ("A","TECH","ものづくり技術コース",True,True),("A","EARLY","幼児教育コース",False,False),
    ("B","JPN","国語コース",False,True),("B","SOC","社会コース",False,True),
    ("B","MATH","数学コース",True,True),("B","SCI","理科コース",True,True),
    ("B","MUSIC","音楽コース",False,False),("B","ART","美術コース",False,True),
    ("B","PE","保健体育コース",False,True),("B","HOME","家庭コース",False,True),
    ("B","TECH","技術コース",True,True),("B","ENG","英語コース",False,True),
    ("B","CALL","書道コース",False,False),("B","INFO","情報コース",True,True),
    ("C","C","特別支援教育",False,True),("D","D","養護教育コース",False,False),
    ("E","LIFE","生涯学習・文化遺産教育コース",False,True),
    ("E","COUN","カウンセリングコース",False,True),
    ("E","SW","ソーシャルワークコース",False,False),
    ("E","MULTI","多文化共生教育コース",False,True),
    ("E","INFO","情報教育コース",True,True),("E","EXP","表現教育コース",False,False),
    ("E","SPORT","生涯スポーツコース",False,True),
]
DEPT = {
    "A":"初等教育専攻（A類）","B":"中等教育専攻（B類）",
    "C":"特別支援教育専攻（C類）","D":"養護教育専攻（D類）",
    "E":"教育支援専攻（E類）",
}

def blank_row(header):
    return {k: "" for k in header}

def common_row(header, cls, slug, slot, stem, record_id, selection_name, flag):
    r = blank_row(header)
    r.update({
        "record_id": record_id, "admission_year": "2027", "institution_type": "国立",
        "university": "東京学芸大学", "prefecture": "東京都",
        "academic_field": "教育支援" if cls == "E" else "教育・教員養成",
        "stem_flag": "True" if stem else "False", "faculty_school": "教育学部",
        "department": DEPT[cls], "selection_category": "特別選抜",
        "selection_name": selection_name, "slot_type": slot, "capacity": "若干名",
        "international_baccalaureate_flag": "No",
        "private_foreign_student_flag": "No", "returnee_flag": "No",
        "regional_quota_flag": "No", "school_recommendation_required": "No",
        "exclusive_enrollment_status": "不明", "common_test_required": "No",
        "common_test_usage": "大学入学共通テストを免除。",
        "research_activity_level": "not_specified", "research_requirement_required": "Unknown",
        "academic_record_required": "Unknown", "selection_document_review": "Yes",
        "selection_interview": "Unknown", "selection_oral_exam": "Unknown",
        "selection_presentation": "Unknown", "selection_essay": "Unknown",
        "selection_written_exam": "Unknown", "selection_practical": "Unknown",
        "selection_group_discussion": "Unknown", "selection_aptitude_test": "Unknown",
        "selection_common_test": "No",
        "source_status": "2027年度公式入学者選抜要項確認済・詳細学生募集要項待ち",
        "detail_completeness": "partial（詳細学生募集要項公開待ち）",
        "verification_grade": "A", "verified_on": "2026-09-28",
        "source_url": "https://www.u-gakugei.ac.jp/nyushi/gakubu/guidebook.html",
        "schedule_url": "https://www.u-gakugei.ac.jp/nyushi/gakubu/",
        "guideline_url": "https://www.u-gakugei.ac.jp/nyushi/upload/2027_tgu_nyusen_colored.pdf",
        "information_year": "2027", "publication_status": "2027年度公式情報（一部詳細要項待ち）",
        "fallback_previous_year": "No",
        "notes": "2026-09-28 Coverage再監査で公式2027入学者選抜要項から募集単位を新規追加。詳細学生募集要項は10月上旬公表予定のため未確定項目はUnknownで保持しUpdateQueueで追跡。",
    })
    r[flag] = "Yes"
    return r

def ib_row(header, c):
    cls, slug, slot, stem, _ = c
    r = common_row(header, cls, slug, slot, stem, f"TGU-2027-IB-{cls}-{slug}",
                   "国際バカロレア選抜", "international_baccalaureate_flag")
    r.update({
        "exclusive_enrollment": "2027年度公式学生募集要項で合格時の入学確約・併願可の明示を確認できないため不明。",
        "eligibility_graduation": "国際バカロレア資格（IB Diploma）を取得した者又は2027年3月31日までに取得見込みの者。",
        "gpa_requirement": "IBスコアの数値下限の明示なし。",
        "english_requirement": "外部英語資格要件なし。",
        "subject_prerequisites": "日本語を母語とする者、又は日本語A（SL/HL）・日本語B（HL）のいずれかを履修した者。",
        "research_requirement_required": "No", "academic_record_required": "Yes",
        "academic_record_type": "国際バカロレア資格の最終試験6科目の成績評価証明書 / Predicted Grades",
        "academic_record_detail": "IB資格取得者は最終試験6科目の成績評価証明書、取得見込み者は学校が作成したPredicted Grades等を提出。",
        "documents_summary": "IB成績関係書類、入学希望理由書等（コースにより活動・作品等の追加資料あり）",
        "selection_process": "大学入学共通テストを免除し、東京学芸大学入学試験（面接試問）と出願書類を総合して判定。",
        "selection_interview": "Yes", "selection_oral_exam": "Yes",
        "selection_presentation": "No", "selection_essay": "No",
        "selection_written_exam": "No", "selection_practical": "No",
        "selection_group_discussion": "No", "selection_aptitude_test": "No",
        "interview_detail": "面接試問。コースに応じて専門性・適性等を確認。",
        "oral_exam_subjects": "コース別", "oral_exam_detail": "面接試問として実施。",
        "selection_method_detail": "出願書類と面接試問を総合して判定。",
        "application_start": "2026-10-01", "application_end": "2026-10-07",
        "web_registration_period": "2026-09-24 09:00～2026-10-07 09:00",
        "second_stage_start": "2026-11-20" if slot in {"保健体育コース","生涯スポーツコース"} else "2026-11-19",
        "second_stage_end": "2026-11-20" if slot in {"保健体育コース","生涯スポーツコース"} else "2026-11-19",
        "final_result_date": "2026-12-03",
        "source_status": "2027年度公式国際バカロレア選抜学生募集要項確認済",
        "detail_completeness": "detailed（4特別選抜フラグ反映済）",
        "source_url": "https://www.u-gakugei.ac.jp/nyushi/gakubu/r9.html",
        "guideline_url": "https://www.u-gakugei.ac.jp/nyushi/upload/2027_tgu_ib_appguide.pdf",
        "publication_status": "2027年度公式情報",
        "notes": "2026-09-28 Coverage再監査で国際バカロレア選抜を募集単位別に新規収録。公式2027学生募集要項で出願資格・日程・選考方法・提出書類を確認。",
    })
    return r

def returnee_row(header, c):
    cls, slug, slot, stem, _ = c
    r = common_row(header, cls, slug, slot, stem, f"TGU-2027-RET-{cls}-{slug}",
                   "帰国生選抜", "returnee_flag")
    r.update({
        "exclusive_enrollment": "2027年度入学者選抜要項に入学確約・併願可の明示を確認できず、詳細学生募集要項公開後に再確認。",
        "eligibility_graduation": "日本国籍又は日本の永住資格等を有し、海外の学校教育歴について2027年度入学者選抜要項に定める帰国生選抜の出願資格を満たす者。",
        "gpa_requirement": "詳細学生募集要項で確認待ち。",
        "english_requirement": "詳細学生募集要項で確認待ち。",
        "subject_prerequisites": "海外学校教育歴等の出願資格を満たすこと。詳細条件は2027年度入学者選抜要項及び学生募集要項による。",
        "documents_summary": "詳細学生募集要項（10月上旬公表予定）で確認待ち。",
        "selection_process": "大学入学共通テストを免除し、東京学芸大学入学試験と出願書類を総合して判定。コース別詳細は学生募集要項公開後に再確認。",
        "application_start": "2026-12-15", "application_end": "2026-12-17",
        "web_registration_period": "Unknown", "second_stage_start": "2027-02-25",
        "second_stage_end": "2027-02-26", "final_result_date": "Unknown",
    })
    return r

def foreign_row(header, c):
    cls, slug, slot, stem, _ = c
    r = common_row(header, cls, slug, slot, stem, f"TGU-2027-FOR-{cls}-{slug}",
                   "私費外国人留学生選抜", "private_foreign_student_flag")
    r.update({
        "exclusive_enrollment": "2027年度入学者選抜要項に入学確約・併願可の明示を確認できず、詳細学生募集要項公開後に再確認。",
        "eligibility_graduation": "外国籍（日本の永住者を除く）で、外国において学校教育12年の課程を修了した者等、2027年度入学者選抜要項に定める資格を満たす者。",
        "gpa_requirement": "詳細学生募集要項で確認待ち。",
        "english_requirement": "詳細学生募集要項で確認待ち。",
        "subject_prerequisites": "日本留学試験（2025年度又は2026年度）の指定科目を受験し、日本語200点以上かつ理科・数学又は総合科目・数学の合計200点以上等の要件を満たすこと。",
        "documents_summary": "詳細学生募集要項（10月上旬公表予定）で確認待ち。",
        "selection_process": "大学入学共通テストを免除し、東京学芸大学入学試験と出願書類を総合して判定。コース別詳細は学生募集要項公開後に再確認。",
        "application_start": "2026-12-15", "application_end": "2026-12-17",
        "web_registration_period": "Unknown", "second_stage_start": "2027-02-25",
        "second_stage_end": "2027-02-26", "final_result_date": "Unknown",
    })
    return r

def update_coverages():
    h, rows = read_csv(KOK_COVERAGE)
    row = next(r for r in rows if r["university"] == "東京学芸大学")
    row.update({
        "research_status": "Master反映済・2027 Coverage再監査中",
        "master_rows": "133",
        "current_year_status": "2027年度情報を反映（一部詳細要項公開待ち）",
        "checked_on": "2026-09-28",
        "official_source_url": "https://www.u-gakugei.ac.jp/nyushi/gakubu/guidebook.html",
        "notes": "2026-09-28 Coverage再監査：既存33行に国際バカロレア28・帰国生36・私費外国人留学生36を追加し計133行。IBは詳細要項確認済。帰国生・私費外国人留学生は10月上旬の学生募集要項待ち。4特殊選抜フラグv5.82反映。",
    })
    write_csv(KOK_COVERAGE, h, rows)

    h, rows = read_csv(OPS_COVERAGE)
    row = next(r for r in rows if r["source_dataset"] == "kokkoritsu" and r["university"] == "東京学芸大学")
    row.update({
        "reaudit_status": "要項公開待ち", "official_system_checked": "実施済",
        "capacity_table_checked": "実施済", "schedule_checked": "実施済",
        "guideline_index_checked": "実施済", "master_compared": "実施済",
        "kawai_crosscheck": "実施不能", "missing_candidate_count": "0",
        "ambiguous_candidate_count": "0", "obsolete_candidate_count": "0",
        "update_queue_open_count": "2", "last_audited_on": "2026-09-28",
        "notes": "2027公式入試体系とMasterを再照合。既存33行にIB28・帰国生36・私費外国人留学生36の計100行を追加し現在133行。IB詳細要項は反映済。帰国生・私費外国人留学生は10月上旬公開予定でUpdateQueue 2件を維持。Kei-Netは2026年度表示のため2027クロスチェック実施不能。",
    })
    write_csv(OPS_COVERAGE, h, rows)

def update_correction():
    items = [json.loads(x) for x in CORRECTIONS.read_text(encoding="utf-8").splitlines() if x.strip()]
    for item in items:
        if item.get("correction_id") == "CC-2027-0002":
            item["status"] = "applied_partial_pending_detail"
            item["applied_on"] = "2026-09-28"
            item["applied_master_rows"] = 100
            item["current_university_master_rows"] = 133
            item["audit_note"] = "100 missing application units added to working Master. IB 28 detailed; returnee 36 and private-foreign 36 remain partial pending early-October student guidelines."
    CORRECTIONS.write_text("\n".join(json.dumps(x, ensure_ascii=False, separators=(",", ":")) for x in items) + "\n", encoding="utf-8")

def main():
    kh, krows = migrate_existing(KOK_MASTER)
    sh, srows = migrate_existing(SHI_MASTER)

    # Idempotent: remove any previous generated TGU special rows first.
    krows = [r for r in krows if not (
        r.get("university") == "東京学芸大学"
        and re.match(r"^TGU-2027-(?:IB|RET|FOR)-", r.get("record_id", ""))
    )]

    ib = [ib_row(kh, c) for c in COURSES if c[4]]
    ret = [returnee_row(kh, c) for c in COURSES]
    foreign = [foreign_row(kh, c) for c in COURSES]
    krows.extend(ib + ret + foreign)

    write_csv(KOK_MASTER, kh, krows)
    write_csv(SHI_MASTER, sh, srows)
    update_coverages()
    update_correction()

    ids = [r["record_id"] for r in krows]
    tgu = [r for r in krows if r.get("university") == "東京学芸大学"]
    counts = {f: sum(r.get(f) == "Yes" for r in tgu) for f in FLAGS}
    assert len(kh) == 79 and len(sh) == 79
    assert len(krows) == 4111
    assert len(srows) == 2400
    assert len(ids) == len(set(ids))
    assert len(tgu) == 133
    assert len(ib) == 28 and len(ret) == 36 and len(foreign) == 36
    assert counts == {
        "international_baccalaureate_flag": 28,
        "private_foreign_student_flag": 36,
        "returnee_flag": 36,
        "regional_quota_flag": 0,
    }
    print(json.dumps({
        "kokkoritsu_rows": len(krows), "shidai_rows": len(srows),
        "master_columns": 79, "tokyo_gakugei_rows": len(tgu),
        "tokyo_gakugei_flags": counts,
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
