#!/usr/bin/env python3
"""One-shot 2027 re-audit for Tokyo University of Marine Science and Technology."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "data/canonical/kokkoritsu/master.csv"
COVERAGE = ROOT / "data/canonical/kokkoritsu/coverage.csv"
OPS = ROOT / "data/operations/coverage_reaudit_2027.csv"
KAWAI = ROOT / "data/operations/kawai_coverage_audit_2027.csv"
QUEUE = ROOT / "data/operations/update_queue.csv"
PILOT = ROOT / "data/operations/candidate_fields_pilot_2027.csv"
CORR = ROOT / "data/operations/canonical_corrections_2027.jsonl"
LEGACY = ROOT / "data/releases/kokkoritsu-v5.61/kokkoritsu_early_admissions_2027_master_v5_61.csv"

REQ = "https://www.kaiyodai.ac.jp/entranceexamination/undergraduate/requirements/"
GUIDE = "https://www.kaiyodai.ac.jp/upload-file/cbd05ed529f16fd6a5983350652bf32c5629582c.pdf"
ENG_GUIDE = "https://www.kaiyodai.ac.jp/upload-file/19a35f5182719abf939e49544146e13dc35c8f7e.pdf"
LIFE_NEWS = "https://www.kaiyodai.ac.jp/news/e_undergraduate/detail/82026_12.html"

def read(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        return list(r.fieldnames or []), [dict(x) for x in r]

def write(path, header, rows):
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header, lineterminator="\n", extrasaction="raise")
        w.writeheader()
        w.writerows(rows)

def blank(header):
    return {k: "" for k in header}

def upsert(rows, key, row):
    for i, old in enumerate(rows):
        if old.get(key) == row.get(key):
            rows[i] = row
            return
    rows.append(row)

PFI = [
    ("BIO", "海洋生命科学部", "海洋生物資源学科", "海洋・生命", "life"),
    ("FOOD", "海洋生命科学部", "食品生産科学科", "食品・生命", "life"),
    ("POLICY", "海洋生命科学部", "海洋政策文化学科", "海洋政策・社会", "life"),
    ("ENG-NAV", "海洋工学部", "海事システム工学科", "海洋工学", "engineering"),
    ("ENG-MECH", "海洋工学部", "海洋電子機械工学科", "海洋・機械電気", "engineering"),
    ("ENG-LOGI", "海洋工学部", "流通情報工学科", "物流・情報", "engineering"),
    ("RES-ENV", "海洋資源環境学部", "海洋環境科学科", "海洋・環境", "resource"),
    ("RES-ENERGY", "海洋資源環境学部", "海洋資源エネルギー学科", "海洋資源・エネルギー", "resource"),
]

def restore_adult_rows(header):
    old_h, old_rows = read(LEGACY)
    source = [
        r for r in old_rows
        if r.get("university") == "東京海洋大学"
        and re.match(r"^TUMSAT-2027-E-", r.get("record_id", ""))
    ]
    assert len(source) == 8
    out = []
    for old in source:
        r = blank(header)
        for k in old_h:
            if k in r:
                r[k] = old.get(k, "")
        for flag in (
            "international_baccalaureate_flag",
            "private_foreign_student_flag",
            "returnee_flag",
            "regional_quota_flag",
            "adult_selection_flag",
        ):
            r[flag] = "No"
        r["adult_selection_flag"] = "Yes"
        r["selection_name"] = "総合型選抜E（社会人）"
        r["slot_type"] = "E（社会人）"
        r["verified_on"] = "2026-09-28"
        r["notes"] = (
            (r.get("notes", "") + " ").strip()
            + "2026-09-28 Coverage再監査：旧v5.61の詳細行を現行スコープへ再収録し、"
              "adult_selection_flag=Yesを付与。2027年度公式資料で再確認。"
        )
        out.append(r)
    return out

def pfi_row(header, code, faculty, dept, field, group):
    r = blank(header)
    r.update({
        "record_id": f"TUMSAT-2027-PFI-{code}",
        "admission_year": "2027",
        "institution_type": "国立",
        "university": "東京海洋大学",
        "prefecture": "東京都",
        "academic_field": field,
        "stem_flag": "True",
        "faculty_school": faculty,
        "department": dept,
        "selection_category": "特別選抜",
        "selection_name": "私費外国人留学生特別入試",
        "slot_type": "私費外国人留学生",
        "capacity": "若干名",
        "international_baccalaureate_flag": "No",
        "private_foreign_student_flag": "Yes",
        "returnee_flag": "No",
        "regional_quota_flag": "No",
        "adult_selection_flag": "No",
        "school_recommendation_required": "No",
        "exclusive_enrollment_status": "不明",
        "exclusive_enrollment": "2027年度入学者選抜要項では合格時の入学確約・併願可の明示を確認できず、詳細学生募集要項待ち。",
        "eligibility_graduation": "外国における12年の学校教育課程を修了又は2027年3月31日までに修了見込み等。その他の出願資格は2026年12月公表予定の学生募集要項で確認。",
        "gpa_requirement": "不明（2027年度私費外国人留学生特別入試学生募集要項は2026年12月頃公表予定）。",
        "common_test_required": "No",
        "common_test_usage": "大学入学共通テストを免除。日本留学試験の指定科目を利用。",
        "research_activity_level": "not_specified",
        "research_requirement_required": "No",
        "academic_record_required": "Unknown",
        "academic_record_detail": "提出書類を選抜資料として使用するが、成績関係書類の正式名称・要否は2026年12月公表予定の学生募集要項で確定する。",
        "documents_summary": "提出書類あり。詳細は2026年12月公表予定の私費外国人留学生特別入試学生募集要項で確認。",
        "selection_process": "教科・科目に係る個別テスト＋面接＋日本留学試験成績＋提出書類を総合して判定。",
        "selection_document_review": "Yes",
        "selection_interview": "Yes",
        "selection_oral_exam": "Unknown",
        "selection_presentation": "No",
        "selection_essay": "Unknown",
        "selection_written_exam": "Yes",
        "selection_practical": "No",
        "selection_group_discussion": "No",
        "selection_aptitude_test": "No",
        "selection_common_test": "No",
        "written_exam_detail": "教科・科目に係る個別テスト。詳細科目・内容は2026年12月公表予定の学生募集要項で確定。",
        "application_start": "2027-01-25",
        "application_end": "2027-02-03",
        "second_stage_start": "2027-02-25",
        "second_stage_end": "2027-02-25",
        "final_result_date": "2027-03-08",
        "source_status": "2027年度入学者選抜要項確認済・私費外国人留学生特別入試学生募集要項12月公表予定",
        "detail_completeness": "partial（詳細学生募集要項公開待ち）",
        "verification_grade": "B",
        "verified_on": "2026-09-28",
        "source_url": REQ,
        "schedule_url": REQ,
        "guideline_url": GUIDE,
        "notes": "2026-09-28 Coverage再監査：2027年度入学者選抜要項で私費外国人留学生特別入試の募集単位を確認し構造反映。詳細学生募集要項は2026年12月頃公表予定。",
        "information_year": "2027",
        "publication_status": "2027年度入学者選抜要項公開済・詳細学生募集要項未公開",
        "fallback_previous_year": "No",
        "current_year_release_expected": "2026年12月頃",
    })
    if group == "engineering":
        r["english_requirement"] = "日本留学試験に加え、個別テストで英語を課す。外部英語資格の要否は詳細学生募集要項待ち。"
        r["subject_prerequisites"] = "2026年度日本留学試験：日本語、理科（物理・化学）、数学（コース2）を日本語で受験。"
        r["written_exam_detail"] = "教科・科目に係る個別テストで数学・英語を課す。詳細は2026年12月公表予定の学生募集要項で確定。"
    elif group == "life":
        r["english_requirement"] = "海洋生命科学部が指定するいずれかの外部英語資格等を保持すること。"
        r["subject_prerequisites"] = "2026年度日本留学試験：日本語、理科（2科目選択）、数学（コース2）を日本語で受験。"
    else:
        r["english_requirement"] = "海洋資源環境学部が指定するいずれかの外部英語資格等を保持すること。"
        r["subject_prerequisites"] = "2026年度日本留学試験：日本語、理科（2科目選択）、数学（コース2）を日本語で受験。"
    return r

def main():
    header, rows = read(MASTER)
    before = len(rows)

    # Idempotent rebuild of Tokyo Marine adult/private-foreign additions.
    rows = [
        r for r in rows
        if not (
            r.get("university") == "東京海洋大学"
            and re.match(r"^TUMSAT-2027-(?:E-|PFI-)", r.get("record_id", ""))
        )
    ]
    adults = restore_adult_rows(header)
    pfi = [pfi_row(header, *x) for x in PFI]
    rows.extend(adults + pfi)
    write(MASTER, header, rows)

    h2, cov = read(COVERAGE)
    c = next(x for x in cov if x["university"] == "東京海洋大学")
    c.update({
        "research_status": "Master反映済・私費外国人留学生詳細要項待ち",
        "master_rows": "50",
        "current_year_status": "2027年度情報を反映（一部12月詳細要項待ち）",
        "fallback_status": "不要（現行情報あり）",
        "checked_on": "2026-09-28",
        "official_source_url": REQ,
        "notes": "2026-09-28 Coverage再監査：公式2027入試体系を再照合。現行34行に総合型E（社会人）8行を旧v5.61から再収録し、私費外国人留学生特別入試8学科を新規追加して計50行。社会人Eは2027公式要項で再確認済み。私費外国人留学生の詳細学生募集要項は12月頃公表予定のためUpdateQueueで追跡。",
    })
    write(COVERAGE, h2, cov)

    h3, ops = read(OPS)
    o = next(x for x in ops if x["source_dataset"] == "kokkoritsu" and x["university"] == "東京海洋大学")
    o.update({
        "reaudit_status": "要項公開待ち",
        "official_system_checked": "実施済",
        "capacity_table_checked": "実施済",
        "schedule_checked": "実施済",
        "guideline_index_checked": "実施済",
        "master_compared": "実施済",
        "kawai_crosscheck": "実施済",
        "missing_candidate_count": "0",
        "ambiguous_candidate_count": "0",
        "obsolete_candidate_count": "0",
        "update_queue_open_count": "1",
        "last_audited_on": "2026-09-28",
        "notes": "2027公式体系・募集人員・日程・要項一覧とMasterを照合。社会人E 8募集単位を現行スコープへ再収録、私費外国人留学生8募集単位を追加し34→50行。Kei-Net 2027推薦・総合型は通常掲載範囲をクロスチェック済み。私費外国人留学生の詳細要項は12月公開待ち。",
    })
    write(OPS, h3, ops)

    h4, kawai = read(KAWAI)
    k = next(x for x in kawai if x["source_dataset"] == "kokkoritsu" and x["university"] == "東京海洋大学")
    k.update({
        "kawai_crosscheck_status": "実施済",
        "missing_candidate_status": "なし（Kei-Net掲載範囲）",
        "official_confirmation_status": "確認済",
        "last_checked_on": "2026-09-28",
        "notes": "Kei-Net 2027推薦・総合型の掲載範囲をMasterとクロスチェック。社会人E・私費外国人留学生は大学公式2027入試体系を確定根拠として確認し、Masterへ反映。",
    })
    write(KAWAI, h4, kawai)

    h5, q = read(QUEUE)
    qr = blank(h5)
    qr.update({
        "queue_id": "UQ-2027-0041",
        "institution_type": "国立",
        "university": "東京海洋大学",
        "faculty_school": "海洋生命科学部・海洋工学部・海洋資源環境学部",
        "selection_name": "私費外国人留学生特別入試",
        "document_type": "学生募集要項",
        "publication_status": "公開予定",
        "release_expected_text": "2026年12月頃（募集要項ページでは12月上旬）",
        "release_expected_from": "2026-12-01",
        "release_expected_to": "2026-12-10",
        "release_schedule_url": REQ,
        "last_checked_on": "2026-09-28",
        "next_check_on": "2026-12-01",
        "action_status": "待機",
        "notes": "2027年度入学者選抜要項で3学部8学科の募集単位・日程・EJU科目・選抜方法を確認しMasterへpartial反映済み。詳細学生募集要項公開後、出願資格、提出書類、個別テスト詳細、入学手続期限等を再監査する。",
    })
    upsert(q, "queue_id", qr)
    write(QUEUE, h5, q)

    h6, pilot = read(PILOT)
    def pilot_row(rid, faculty, dept, sel, deadline, deadline_detail, grad_status, grad_detail, regional, regional_detail, gender, gender_detail, url, note):
        x = blank(h6)
        x.update({
            "source_dataset": "kokkoritsu",
            "record_id": rid,
            "university": "東京海洋大学",
            "faculty_school": faculty,
            "department": dept,
            "selection_name": sel,
            "slot_type": "E（社会人）" if "-E-" in rid else "私費外国人留学生",
            "enrollment_procedure_deadline": deadline,
            "enrollment_procedure_detail": deadline_detail,
            "graduation_eligibility_status": grad_status,
            "graduation_eligibility_detail": grad_detail,
            "regional_requirement_status": regional,
            "regional_requirement_detail": regional_detail,
            "gender_requirement": gender,
            "gender_requirement_detail": gender_detail,
            "guideline_url": url,
            "reviewed_on": "2026-09-28",
            "pilot_status": "pilot",
            "notes": note,
        })
        return x

    reps = [
        pilot_row(
            "TUMSAT-2027-E-ENG-NAV", "海洋工学部", "海事システム工学科", "総合型選抜E（社会人）",
            "2026-11-20", "海洋工学部総合型選抜の入学手続期間は2026-11-13～11-20（必着）。",
            "その他", "2027年3月31日までに満23歳、社会人経験通算5年以上。",
            "Unknown", "2027年度公式募集要項に地域居住・高校所在地等の地域条件の明示なし。",
            "制限なし", "出願資格上の性別制限なし。船舶系では男女別の身体基準があるが、男女双方を対象としている。",
            ENG_GUIDE, "社会人E代表。4候補項目を2027年度公式募集要項からpilot収集。"
        ),
        pilot_row(
            "TUMSAT-2027-PFI-BIO", "海洋生命科学部", "海洋生物資源学科", "私費外国人留学生特別入試",
            "", "入学手続期限は2026年12月公表予定の詳細学生募集要項で確認。",
            "その他", "外国における12年課程修了又は2027年3月31日までに修了見込み等。その他資格は詳細要項待ち。",
            "Unknown", "外国課程要件はあるが、地域居住・高校所在地等の地域条件としては詳細要項公開後に再確認。",
            "不明", "詳細学生募集要項公開後に性別条件の明示有無を再確認。",
            GUIDE, "私費外国人留学生代表。未公開詳細は推測せずUpdateQueueへ。"
        ),
    ]
    for x in reps:
        upsert(pilot, "record_id", x)
    write(PILOT, h6, pilot)

    items = [json.loads(x) for x in CORR.read_text(encoding="utf-8").splitlines() if x.strip()]
    cc = {
        "correction_id": "CC-2027-0005",
        "dataset": "kokkoritsu",
        "university": "東京海洋大学",
        "detected_on": "2026-09-28",
        "status": "applied_partial_pending_detail",
        "reason": "Coverage re-audit found adult comprehensive-selection rows removed by former scope policy and a current-year private-foreign selection absent from canonical Master.",
        "existing_master_rows": 34,
        "restored_selection_groups": [
            {"selection_name": "総合型選抜E（社会人）", "confirmed_units": 8, "source": "legacy v5.61 rows reverified against 2027 official sources"}
        ],
        "missing_selection_groups": [
            {"selection_name": "私費外国人留学生特別入試", "confirmed_units": 8, "apply_status": "applied_partial", "update_queue_id": "UQ-2027-0041"}
        ],
        "confirmed_additional_units_total": 16,
        "applied_master_rows": 16,
        "current_university_master_rows": 50,
        "official_source": "2027年度東京海洋大学 入学者選抜要項・各総合型選抜学生募集要項",
        "official_url": REQ,
        "audit_note": "Adult E 8 units restored under the current special-selection scope. Private-foreign 8 units added from the official 2027 selection guide; its detailed student guide remains queued for December.",
    }
    items = [x for x in items if x.get("correction_id") != "CC-2027-0005"] + [cc]
    CORR.write_text("\n".join(json.dumps(x, ensure_ascii=False, separators=(",", ":")) for x in items) + "\n", encoding="utf-8")

    ids = [r["record_id"] for r in rows]
    tumsat = [r for r in rows if r.get("university") == "東京海洋大学"]
    assert len(rows) == before + 16
    assert len(ids) == len(set(ids))
    assert len(tumsat) == 50
    assert sum(r.get("adult_selection_flag") == "Yes" for r in tumsat) == 8
    assert sum(r.get("private_foreign_student_flag") == "Yes" for r in tumsat) == 8
    assert sum(r.get("returnee_flag") == "Yes" for r in tumsat) == 8
    assert sum(r.get("international_baccalaureate_flag") == "Yes" for r in tumsat) == 0
    assert sum(r.get("regional_quota_flag") == "Yes" for r in tumsat) == 0
    assert len(adults) == 8 and len(pfi) == 8

    print(json.dumps({
        "kokkoritsu_rows_before": before,
        "kokkoritsu_rows_after": len(rows),
        "tumsat_rows": len(tumsat),
        "tumsat_adult_e": 8,
        "tumsat_private_foreign": 8,
        "update_queue_id": "UQ-2027-0041",
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
