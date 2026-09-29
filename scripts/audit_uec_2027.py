#!/usr/bin/env python3
"""One-shot 2027 re-audit for The University of Electro-Communications."""

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

TYPE_PAGE = "https://www.uec.ac.jp/education/undergraduate/admission/senbatsu_type.html"
GUIDE = "https://www.uec.ac.jp/education/undergraduate/admission/pdf/2027senbatsu.pdf"
REQUEST = "https://www.uec.ac.jp/education/undergraduate/admission/request.html"

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

UNITS = [
    ("I", "Ⅰ類（情報系）", "情報・データサイエンス"),
    ("II", "Ⅱ類（融合系）", "情報・工学"),
    ("III", "Ⅲ類（理工系）", "理工"),
]

def pfi_row(header, code, dept, field):
    r = blank(header)
    r.update({
        "record_id": f"UEC-2027-PFI-{code}",
        "admission_year": "2027",
        "institution_type": "国立",
        "university": "電気通信大学",
        "prefecture": "東京都",
        "academic_field": field,
        "stem_flag": "True",
        "faculty_school": "情報理工学域",
        "department": dept,
        "selection_category": "特別選抜",
        "selection_name": "一般選抜（私費外国人留学生）",
        "slot_type": dept,
        "international_baccalaureate_flag": "No",
        "private_foreign_student_flag": "Yes",
        "returnee_flag": "No",
        "regional_quota_flag": "No",
        "adult_selection_flag": "No",
        "capacity": "若干名",
        "school_recommendation_required": "No",
        "exclusive_enrollment_status": "不明",
        "exclusive_enrollment": "2027年度入学者選抜要項に、合格時の入学確約又は併願可の明示を確認できないため不明。",
        "eligibility_graduation": "日本国籍を有しない者で、外国の12年課程修了・2027年3月31日までに修了見込み、IB等の大学入学資格等のいずれかを満たし、2026年度日本留学試験および所定のTOEFL/TOEIC要件を満たす者。日本の高校・中等教育学校卒業者および日本国永住者は対象外。",
        "gpa_requirement": "数値による評定要件の明示なし。出身学校等の成績を選抜資料として使用。",
        "english_requirement": "2025年4月以降受検のTOEFL iBT 46点以上、又はTOEIC L&R 450点以上。",
        "subject_prerequisites": "2026年度日本留学試験で、日本語、理科（物理・化学）、数学（コース2）を受験すること。",
        "common_test_required": "No",
        "common_test_usage": "大学入学共通テストは課さず、日本留学試験を利用。",
        "research_activity_level": "not_specified",
        "research_requirement_required": "No",
        "academic_record_required": "Unknown",
        "academic_record_detail": "2027年度入学者選抜要項では出身学校等の成績を選抜資料として使用することを確認。提出する成績関係書類の正式名称は11月上旬公開予定の詳細募集要項で確定する。",
        "documents_summary": "TOEFL/TOEICスコア証明書等。その他の提出書類は2026年11月上旬公開予定の私費外国人留学生選抜募集要項で確認。",
        "selection_process": "日本留学試験、本学の学力検査、面接試験、出身学校等の成績を総合して判定。",
        "selection_document_review": "Yes",
        "selection_interview": "Yes",
        "selection_oral_exam": "No",
        "selection_presentation": "No",
        "selection_essay": "No",
        "selection_written_exam": "Yes",
        "selection_practical": "No",
        "selection_group_discussion": "No",
        "selection_aptitude_test": "No",
        "selection_common_test": "No",
        "interview_detail": "2027年2月27日に面接試験を実施。詳細は11月上旬公開予定の募集要項で確認。",
        "written_exam_detail": "2027年2月25日に学力検査。数学120分、物理・化学・情報の3科目から2科目を選択（120分）、日本語75分。数学200点、理科・情報200点、日本語100点。",
        "selection_method_detail": "類の志望は第2志望まで可。日本留学試験＋本学学力検査＋面接＋出身学校等の成績を総合評価。",
        "application_start": "2027-01-18",
        "application_end": "2027-01-20",
        "second_stage_start": "2027-02-25",
        "second_stage_end": "2027-02-27",
        "final_result_date": "2027-03-06",
        "source_status": "2027年度入学者選抜要項確認済・私費外国人留学生選抜詳細募集要項11月上旬公開予定",
        "detail_completeness": "partial（私費外国人留学生選抜詳細募集要項公開待ち）",
        "verification_grade": "A",
        "verified_on": "2026-09-28",
        "source_url": TYPE_PAGE,
        "schedule_url": GUIDE,
        "guideline_url": GUIDE,
        "notes": "2026-09-28 Coverage再監査で2027年度公式入学者選抜要項から新規収録。類別募集3単位を構造反映。詳細募集要項は11月上旬公開予定のため、提出書類等は推測せずUpdateQueueで追跡。",
        "information_year": "2027",
        "publication_status": "2027年度入学者選抜要項公開済・詳細募集要項未公開",
        "fallback_previous_year": "No",
        "current_year_release_expected": "2026年11月上旬",
    })
    return r

def main():
    header, rows = read(MASTER)
    rows = [
        r for r in rows
        if not (
            r.get("university") == "電気通信大学"
            and re.match(r"^UEC-2027-PFI-", r.get("record_id", ""))
        )
    ]
    base = len(rows)
    additions = [pfi_row(header, *x) for x in UNITS]
    rows.extend(additions)
    write(MASTER, header, rows)

    h2, cov = read(COVERAGE)
    c = next(x for x in cov if x["university"] == "電気通信大学")
    c.update({
        "research_status": "Master反映済・私費外国人留学生詳細要項待ち",
        "master_rows": "22",
        "current_year_status": "2027年度情報を反映（一部11月詳細要項待ち）",
        "fallback_status": "不要（現行情報あり）",
        "checked_on": "2026-09-28",
        "official_source_url": TYPE_PAGE,
        "notes": "2026-09-28 Coverage再監査：2027年度公式入試体系・募集人員・日程・要項一覧を確認。既存19行（総合型4＋学校推薦15）に私費外国人留学生3類を追加し計22行。帰国子女・独立した社会人選抜は2027公式体系で確認されず。私費外国人留学生の詳細募集要項は11月上旬公開予定のためUpdateQueueで追跡。",
    })
    write(COVERAGE, h2, cov)

    h3, ops = read(OPS)
    o = next(x for x in ops if x["source_dataset"] == "kokkoritsu" and x["university"] == "電気通信大学")
    o.update({
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
        "update_queue_open_count": "1",
        "last_audited_on": "2026-09-28",
        "notes": "2027公式体系とMasterを照合し、私費外国人留学生3類を追加して19→22行。総合型4・学校推薦15は公式2027募集単位と対応。Kei-Netは総合型が2027、推薦が2026表示のため全体系の2027クロスチェックは実施不能として理由を記録。私費外国人留学生詳細要項は11月上旬待ち。",
    })
    write(OPS, h3, ops)

    h4, kawai = read(KAWAI)
    k = next(x for x in kawai if x["source_dataset"] == "kokkoritsu" and x["university"] == "電気通信大学")
    k.update({
        "kawai_crosscheck_status": "実施不能",
        "missing_candidate_status": "総合型2027は照合済・推薦は2026表示のため2027全体判定不能",
        "official_confirmation_status": "確認済",
        "last_checked_on": "2026-09-28",
        "notes": "Kei-Net総合型2027は既存Masterと照合しmissingなし。学校推薦型は2026年度表示のため2027比較不能。私費外国人留学生はKei-Net推薦・総合型DB対象外のため大学公式2027入学者選抜要項で確認。",
    })
    write(KAWAI, h4, kawai)

    h5, q = read(QUEUE)
    qr = blank(h5)
    qr.update({
        "queue_id": "UQ-2027-0042",
        "institution_type": "国立",
        "university": "電気通信大学",
        "faculty_school": "情報理工学域",
        "selection_name": "一般選抜（私費外国人留学生）",
        "document_type": "学生募集要項",
        "publication_status": "公開予定",
        "release_expected_text": "2026年11月上旬",
        "release_expected_from": "2026-11-01",
        "release_expected_to": "2026-11-10",
        "release_schedule_url": TYPE_PAGE,
        "last_checked_on": "2026-09-28",
        "next_check_on": "2026-11-01",
        "action_status": "待機",
        "notes": "2027年度入学者選抜要項でⅠ・Ⅱ・Ⅲ類の3募集単位、出願資格、EJU/英語要件、選抜方法・日程を確認しMasterへpartial反映済み。11月上旬の詳細募集要項公開後、提出書類、成績関係書類、面接詳細、入学手続期限等を再監査する。",
    })
    upsert(q, "queue_id", qr)
    write(QUEUE, h5, q)

    h6, pilot = read(PILOT)
    def pilot_row(rid, dept, sel, slot, grad_status, years, grad_detail, gender, gender_detail, guide, note):
        x = blank(h6)
        x.update({
            "source_dataset": "kokkoritsu",
            "record_id": rid,
            "university": "電気通信大学",
            "faculty_school": "情報理工学域",
            "department": dept,
            "selection_name": sel,
            "slot_type": slot,
            "enrollment_procedure_deadline": "",
            "enrollment_procedure_detail": "2027年度詳細募集要項で確認。",
            "graduation_eligibility_status": grad_status,
            "years_since_graduation_max": years,
            "graduation_eligibility_detail": grad_detail,
            "regional_requirement_status": "No",
            "regional_requirement_detail": "2027年度公式要項の出願資格に居住地・高校所在地等の地域条件なし。",
            "gender_requirement": gender,
            "gender_requirement_detail": gender_detail,
            "guideline_url": guide,
            "reviewed_on": "2026-09-28",
            "pilot_status": "pilot",
            "notes": note,
        })
        return x

    samples = [
        pilot_row(
            "UEC-2027-REC-I-DDS",
            "Ⅰ類（情報系）／デザイン思考・データサイエンスプログラム",
            "学校推薦型選抜",
            "デザイン思考・データサイエンスプログラム",
            "現役のみ",
            "0",
            "2027年3月卒業・修了見込みを対象。",
            "女性",
            "2027年度入学者選抜要項でデザイン思考・データサイエンスプログラムの学校推薦型5名を女子枠と明記。",
            GUIDE,
            "電通大の性別条件代表例。"
        ),
        pilot_row(
            "UEC-2027-PFI-I",
            "Ⅰ類（情報系）",
            "一般選抜（私費外国人留学生）",
            "Ⅰ類（情報系）",
            "その他",
            "",
            "外国の12年課程修了・2027年3月31日までに修了見込み、IB等の所定資格等。",
            "制限なし",
            "2027年度公式入学者選抜要項に性別制限なし。",
            GUIDE,
            "私費外国人留学生代表。詳細未公開項目はUpdateQueueへ。"
        ),
    ]
    for x in samples:
        upsert(pilot, "record_id", x)
    write(PILOT, h6, pilot)

    items = [json.loads(x) for x in CORR.read_text(encoding="utf-8").splitlines() if x.strip()]
    cc = {
        "correction_id": "CC-2027-0007",
        "dataset": "kokkoritsu",
        "university": "電気通信大学",
        "detected_on": "2026-09-28",
        "status": "applied_partial_pending_detail",
        "reason": "Coverage re-audit found the 2027 private-foreign undergraduate selection absent from canonical Master.",
        "existing_master_rows": 19,
        "missing_selection_groups": [
            {
                "selection_name": "一般選抜（私費外国人留学生）",
                "confirmed_units": 3,
                "grain": "Ⅰ類 / Ⅱ類 / Ⅲ類",
                "apply_status": "applied_partial",
                "update_queue_id": "UQ-2027-0042"
            }
        ],
        "confirmed_missing_units_total": 3,
        "applied_master_rows": 3,
        "current_university_master_rows": 22,
        "official_source": "2027年度電気通信大学 情報理工学域 入学者選抜要項",
        "official_url": GUIDE,
        "audit_note": "Private-foreign selection is explicitly class-based with a few seats in each class. Structural rows were added; detailed student guidelines are scheduled for early November.",
    }
    items = [x for x in items if x.get("correction_id") != "CC-2027-0007"] + [cc]
    CORR.write_text("\n".join(json.dumps(x, ensure_ascii=False, separators=(",", ":")) for x in items) + "\n", encoding="utf-8")

    ids = [r["record_id"] for r in rows]
    uec = [r for r in rows if r.get("university") == "電気通信大学"]
    assert len(rows) == base + 3
    assert len(ids) == len(set(ids))
    assert len(uec) == 22
    assert sum(r.get("private_foreign_student_flag") == "Yes" for r in uec) == 3
    assert sum(r.get("returnee_flag") == "Yes" for r in uec) == 0
    assert sum(r.get("adult_selection_flag") == "Yes" for r in uec) == 0
    assert sum(r.get("regional_quota_flag") == "Yes" for r in uec) == 0
    assert sum(r.get("international_baccalaureate_flag") == "Yes" for r in uec) == 0
    assert len(additions) == 3

    print(json.dumps({
        "kokkoritsu_rows_after": len(rows),
        "uec_rows": len(uec),
        "uec_private_foreign": 3,
        "update_queue_id": "UQ-2027-0042",
        "reaudit_status": "要項公開待ち",
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
