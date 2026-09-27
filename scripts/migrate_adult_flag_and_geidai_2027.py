#!/usr/bin/env python3
"""One-shot 2027 migration: fifth adult-selection flag + Tokyo Geidai coverage expansion."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADULT = "adult_selection_flag"
KOK_MASTER = ROOT / "data/canonical/kokkoritsu/master.csv"
SHI_MASTER = ROOT / "data/canonical/shidai/master.csv"
KOK_COVERAGE = ROOT / "data/canonical/kokkoritsu/coverage.csv"
OPS_COVERAGE = ROOT / "data/operations/coverage_reaudit_2027.csv"
UPDATE_QUEUE = ROOT / "data/operations/update_queue.csv"
CORRECTIONS = ROOT / "data/operations/canonical_corrections_2027.jsonl"

OFFICIAL_GUIDE = "https://admissions.geidai.ac.jp/wp/wp-content/uploads/2026/07/R9nyugakusyasenbatuyoko0727.pdf"
FINE_PAGE = "https://admissions.geidai.ac.jp/undergraduate/fine-arts/application/"
MUSIC_PAGE = "https://admissions.geidai.ac.jp/undergraduate/music/application/"

def read_csv(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        return list(reader.fieldnames or []), [dict(r) for r in reader]

def write_csv(path: Path, header: list[str], rows: list[dict[str, str]]):
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=header, lineterminator="\n", extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)

def ensure_adult_header(header: list[str]) -> list[str]:
    if ADULT in header:
        return header
    pos = header.index("regional_quota_flag") + 1
    return header[:pos] + [ADULT] + header[pos:]

def adult_value(row: dict[str, str]) -> str:
    cat = row.get("selection_category", "")
    name = row.get("selection_name", "")
    slot = row.get("slot_type", "")
    adult = "社会人" in cat or "社会人" in name or "社会人" in slot
    if "内数" in slot and "社会人" in slot and not re.match(r"^社会人", slot):
        adult = False
    return "Yes" if adult else "No"

def migrate_adult(path: Path):
    old_header, rows = read_csv(path)
    header = ensure_adult_header(old_header)
    for row in rows:
        row[ADULT] = adult_value(row)
        for key in header:
            row.setdefault(key, "")
    return header, rows

def blank(header):
    return {key: "" for key in header}

FINE_UNITS = [
    ("FA-JPN","絵画科 日本画専攻","日本画専攻"),
    ("FA-OIL","絵画科 油画専攻","油画専攻"),
    ("FA-SCULP","彫刻科","彫刻科"),
    ("FA-CRAFT","工芸科","工芸科"),
    ("FA-DESIGN","デザイン科","デザイン科"),
    ("FA-ARCH","建築科","建築科"),
    ("FA-INTER","先端芸術表現科","先端芸術表現科"),
    ("FA-AESTH","芸術学科","芸術学科"),
]
RETURN_UNITS = {code for code, _, _ in FINE_UNITS if code in {"FA-OIL","FA-CRAFT","FA-DESIGN","FA-ARCH","FA-INTER"}}
MUSIC_UNITS = [
    ("MU-COMP","作曲科"),
    ("MU-VOCAL","声楽科"),
    ("MU-INSTR","器楽科"),
    ("MU-COND","指揮科"),
    ("MU-TRAD","邦楽科"),
    ("MU-MUSICOLOGY","楽理科"),
    ("MU-CREATIVE","音楽環境創造科"),
]

def common(header, record_id, faculty, department, selection_name, flag=None):
    row = blank(header)
    row.update({
        "record_id": record_id,
        "admission_year": "2027",
        "institution_type": "国立",
        "university": "東京藝術大学",
        "prefecture": "東京都",
        "academic_field": "芸術",
        "stem_flag": "False",
        "faculty_school": faculty,
        "department": department,
        "selection_category": "特別選抜",
        "selection_name": selection_name,
        "slot_type": selection_name,
        "capacity": "若干名",
        "international_baccalaureate_flag": "No",
        "private_foreign_student_flag": "No",
        "returnee_flag": "No",
        "regional_quota_flag": "No",
        "adult_selection_flag": "No",
        "school_recommendation_required": "No",
        "exclusive_enrollment_status": "不明",
        "common_test_required": "No",
        "research_activity_level": "not_specified",
        "research_requirement_required": "No",
        "academic_record_required": "Unknown",
        "selection_document_review": "Yes",
        "selection_interview": "Unknown",
        "selection_oral_exam": "Unknown",
        "selection_presentation": "Unknown",
        "selection_essay": "Unknown",
        "selection_written_exam": "Unknown",
        "selection_practical": "Unknown",
        "selection_group_discussion": "No",
        "selection_aptitude_test": "Unknown",
        "selection_common_test": "No",
        "source_status": "2027年度公式入学者選抜要項確認済・詳細学生募集要項待ち",
        "detail_completeness": "partial（詳細学生募集要項公開待ち）",
        "verification_grade": "A",
        "verified_on": "2026-09-28",
        "source_url": FINE_PAGE if faculty == "美術学部" else MUSIC_PAGE,
        "schedule_url": "https://admissions.geidai.ac.jp/",
        "guideline_url": OFFICIAL_GUIDE,
        "information_year": "2027",
        "publication_status": "2027年度公式情報（一部詳細要項待ち）",
        "fallback_previous_year": "No",
        "notes": "2026-09-28 Coverage再監査で2027年度入学者選抜要項から募集単位を新規追加。詳細学生募集要項公開後に未確定項目を再監査する。",
    })
    if flag:
        row[flag] = "Yes"
    return row

def private_foreign_row(header, faculty, code, department):
    row = common(header, f"GEIDAI-2027-PFI-{code}", faculty, department, "私費外国人留学生入試", "private_foreign_student_flag")
    row.update({
        "eligibility_graduation": "外国籍で大学入学に支障のない在留資格を有する又は取得見込みで、外国の12年課程修了者等、2027年度入学者選抜要項の資格を満たす者。日本の高等学校・中等教育学校卒業者等は対象外。",
        "common_test_usage": "大学入学共通テストは免除。日本留学試験の大学指定科目を受験する。",
        "subject_prerequisites": "2026年6月又は11月実施の日本留学試験について、学部・学科指定科目を受験すること。",
        "selection_process": "本学の個別試験、提出書類及び日本留学試験の成績等を総合して判定。詳細な個別試験は学生募集要項公開後に確定。",
        "documents_summary": "提出書類あり。詳細は学生募集要項公開後に確認。",
    })
    return row

def returnee_row(header, code, department):
    row = common(header, f"GEIDAI-2027-RET-{code}", "美術学部", department, "帰国生徒選抜", "returnee_flag")
    row.update({
        "eligibility_graduation": "日本国籍又は日本の永住許可を得ている者で、外国において最終学年を含め2年以上継続して教育を受け、2027年度入学者選抜要項の資格を満たす者。",
        "common_test_usage": "大学入学共通テストを免除。",
        "selection_process": "一般選抜志願者と同一の試験により選抜し、日本語による面接を課す。先端芸術表現科は第1次で実技（素描）又は小論文を選択。",
        "selection_interview": "Yes",
        "documents_summary": "志望理由書等を提出。先端芸術表現科は個人資料ファイルも提出。",
        "application_start": "2026-12-08",
        "application_end": "2026-12-22",
        "final_result_date": "2027-03-14",
    })
    return row

def foreign_education_row(header, code, department):
    row = common(header, f"GEIDAI-2027-FEC-{code}", "音楽学部", department, "外国教育課程出身者特別入試")
    row.update({
        "eligibility_graduation": "日本国籍又は日本の永住許可を得ている者で、外国における12年課程を2025年4月1日から2027年3月31日までに修了し最終学年を含め2年以上継続して外国教育を受けた者、又は2025年・2026年にIB等の指定外国大学入学資格を取得した者等。",
        "common_test_usage": "大学入学共通テストを免除。",
        "selection_process": "出願書類及び一般選抜志願者と同一の個別試験により選抜し、全学科で日本語による面接を課す。",
        "selection_interview": "Yes",
        "documents_summary": "志望理由書、成績証明書等。音楽環境創造科以外は800字以内の志望理由書を提出。",
        "application_start": "2027-01-25",
        "application_end": "2027-02-03",
        "final_result_date": "2027-03-13",
        "exclusive_enrollment": "東京藝術大学の一般選抜との併願は認めない。",
    })
    return row

def update_coverages():
    header, rows = read_csv(KOK_COVERAGE)
    row = next(r for r in rows if r["university"] == "東京藝術大学")
    row.update({
        "research_status": "Master反映済・2027 Coverage再監査中",
        "master_rows": "30",
        "current_year_status": "2027年度情報を反映（一部詳細要項公開待ち）",
        "checked_on": "2026-09-28",
        "official_source_url": FINE_PAGE,
        "notes": "2026-09-28 Coverage再監査：既存SSP3行に加え、私費外国人留学生15・帰国生徒5・音楽学部外国教育課程出身者7の計27行を2027年度公式入学者選抜要項から追加し計30行。社会人入試は実施しないことを確認。詳細学生募集要項は11月下旬～12月上旬待ち。",
    })
    write_csv(KOK_COVERAGE, header, rows)

    header, rows = read_csv(OPS_COVERAGE)
    row = next(r for r in rows if r["source_dataset"] == "kokkoritsu" and r["university"] == "東京藝術大学")
    row.update({
        "reaudit_status": "要項公開待ち",
        "official_system_checked": "実施済",
        "capacity_table_checked": "実施済",
        "schedule_checked": "実施済",
        "guideline_index_checked": "実施済",
        "master_compared": "実施済",
        "kawai_crosscheck": "実施不能",
        "missing_candidate_count": "0",
        "ambiguous_candidate_count": "0",
        "obsolete_candidate_count": "0",
        "update_queue_open_count": "3",
        "last_audited_on": "2026-09-28",
        "notes": "2027公式入試体系をMasterと照合。既存SSP3行に私費外国人留学生15・帰国生徒5・外国教育課程出身者7を追加し現在30行。社会人入試は公式に非実施。詳細募集要項は11月下旬～12月上旬公開予定のためUpdateQueue 3件。Kei-Netは推薦・総合型を掲載しないためクロスチェック実施不能。",
    })
    write_csv(OPS_COVERAGE, header, rows)

def upsert_queue():
    header, rows = read_csv(UPDATE_QUEUE)
    additions = [
        {
            "queue_id":"UQ-2027-0037","institution_type":"国立","university":"東京藝術大学","faculty_school":"美術学部",
            "selection_name":"私費外国人留学生入試","document_type":"学生募集要項","publication_status":"公開予定",
            "release_expected_text":"2026年11月下旬","release_expected_from":"2026-11-21","release_expected_to":"2026-11-30",
            "release_schedule_url":FINE_PAGE,"last_checked_on":"2026-09-28","next_check_on":"2026-11-21","actual_release_on":"",
            "action_status":"待機","related_record_id":"","notes":"2027入学者選抜要項で美術学部8募集単位を確認。詳細は美術学部学生募集要項公開後に再監査。"
        },
        {
            "queue_id":"UQ-2027-0038","institution_type":"国立","university":"東京藝術大学","faculty_school":"美術学部",
            "selection_name":"帰国生徒選抜","document_type":"学生募集要項","publication_status":"公開予定",
            "release_expected_text":"2026年11月下旬","release_expected_from":"2026-11-21","release_expected_to":"2026-11-30",
            "release_schedule_url":FINE_PAGE,"last_checked_on":"2026-09-28","next_check_on":"2026-11-21","actual_release_on":"",
            "action_status":"待機","related_record_id":"","notes":"2027入学者選抜要項で5募集単位を確認。詳細学生募集要項公開後に再監査。"
        },
        {
            "queue_id":"UQ-2027-0039","institution_type":"国立","university":"東京藝術大学","faculty_school":"音楽学部",
            "selection_name":"私費外国人留学生入試・外国教育課程出身者特別入試","document_type":"学生募集要項","publication_status":"公開予定",
            "release_expected_text":"2026年12月上旬","release_expected_from":"2026-12-01","release_expected_to":"2026-12-10",
            "release_schedule_url":MUSIC_PAGE,"last_checked_on":"2026-09-28","next_check_on":"2026-12-01","actual_release_on":"",
            "action_status":"待機","related_record_id":"","notes":"2027入学者選抜要項で私費外国人留学生7募集単位・外国教育課程出身者7募集単位を確認。詳細学生募集要項公開後に再監査。"
        },
    ]
    index = {r["queue_id"]: i for i, r in enumerate(rows)}
    for item in additions:
        complete = {k: item.get(k, "") for k in header}
        if item["queue_id"] in index:
            rows[index[item["queue_id"]]] = complete
        else:
            rows.append(complete)
    write_csv(UPDATE_QUEUE, header, rows)

def update_corrections():
    items = [json.loads(x) for x in CORRECTIONS.read_text(encoding="utf-8").splitlines() if x.strip()]
    item = {
        "correction_id":"CC-2027-0003","dataset":"kokkoritsu","university":"東京藝術大学","detected_on":"2026-09-28",
        "status":"applied_partial_pending_detail",
        "reason":"Coverage re-audit found three official 2027 special-selection groups absent from working Master.",
        "existing_master_rows":3,
        "existing_groups":[{"selection_name":"音楽学部SSP（飛び入学）","units":3}],
        "missing_selection_groups":[
            {"selection_name":"私費外国人留学生入試","confirmed_units":15,"apply_status":"applied_partial","update_queue_ids":["UQ-2027-0037","UQ-2027-0039"]},
            {"selection_name":"帰国生徒選抜","confirmed_units":5,"apply_status":"applied_partial","update_queue_id":"UQ-2027-0038"},
            {"selection_name":"外国教育課程出身者特別入試","confirmed_units":7,"apply_status":"applied_partial","update_queue_id":"UQ-2027-0039"}
        ],
        "confirmed_missing_units_total":27,
        "applied_master_rows":27,
        "current_university_master_rows":30,
        "official_source":"2027年度東京藝術大学入学者選抜要項",
        "official_url":OFFICIAL_GUIDE,
        "audit_note":"Official 2027 structure confirms private-foreign 15, Fine Arts returnee 5, Music foreign-education 7. Adult admissions are explicitly not offered. Detailed guides remain queued for November/December."
    }
    found = False
    for i, old in enumerate(items):
        if old.get("correction_id") == item["correction_id"]:
            items[i] = item
            found = True
            break
    if not found:
        items.append(item)
    CORRECTIONS.write_text("\n".join(json.dumps(x, ensure_ascii=False, separators=(",", ":")) for x in items) + "\n", encoding="utf-8")

def main():
    kh, krows = migrate_adult(KOK_MASTER)
    sh, srows = migrate_adult(SHI_MASTER)

    # Idempotent: remove generated Geidai rows before rebuilding them.
    krows = [r for r in krows if not (
        r.get("university") == "東京藝術大学"
        and re.match(r"^GEIDAI-2027-(?:PFI|RET|FEC)-", r.get("record_id", ""))
    )]

    pfi = [private_foreign_row(kh, "美術学部", code, dep) for code, dep, _ in FINE_UNITS]
    pfi += [private_foreign_row(kh, "音楽学部", code, dep) for code, dep in MUSIC_UNITS]
    ret = [returnee_row(kh, code, dep) for code, dep, _ in FINE_UNITS if code in RETURN_UNITS]
    fec = [foreign_education_row(kh, code, dep) for code, dep in MUSIC_UNITS]
    krows.extend(pfi + ret + fec)

    write_csv(KOK_MASTER, kh, krows)
    write_csv(SHI_MASTER, sh, srows)
    update_coverages()
    upsert_queue()
    update_corrections()

    ids = [r["record_id"] for r in krows]
    geidai = [r for r in krows if r.get("university") == "東京藝術大学"]
    assert len(kh) == 80 and len(sh) == 80
    assert len(krows) == 4138
    assert len(srows) == 2400
    assert len(ids) == len(set(ids))
    assert len(geidai) == 30
    assert sum(r.get("private_foreign_student_flag") == "Yes" for r in geidai) == 15
    assert sum(r.get("returnee_flag") == "Yes" for r in geidai) == 5
    assert sum(r.get("adult_selection_flag") == "Yes" for r in geidai) == 0
    assert len(pfi) == 15 and len(ret) == 5 and len(fec) == 7

    print(json.dumps({
        "kokkoritsu_rows": len(krows),
        "shidai_rows": len(srows),
        "master_columns": 80,
        "tokyo_geidai_rows": len(geidai),
        "tokyo_geidai_private_foreign": 15,
        "tokyo_geidai_returnee": 5,
        "tokyo_geidai_foreign_education": 7,
        "tokyo_geidai_adult": 0,
        "adult_flag_counts": {
            "kokkoritsu": sum(r.get(ADULT) == "Yes" for r in krows),
            "shidai": sum(r.get(ADULT) == "Yes" for r in srows),
        }
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
