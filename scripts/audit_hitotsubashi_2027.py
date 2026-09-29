#!/usr/bin/env python3
"""One-shot 2027 re-audit update for Hitotsubashi University.

This pass applies only facts confirmed in the 2027 official selection guide:
- add four private-foreign undergraduate application units;
- classify the four Foreign-School-Background Selection rows as returnee;
- populate official 2027 dates/methods that are already explicit in the selection guide;
- register the three detailed guides published on 2026-09-25 for continuing deep review.

The detailed 2027 recommendation/foreign-school/private-foreign guides are published,
but fields not yet directly extracted from those documents remain Unknown/partial.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "data/canonical/kokkoritsu/master.csv"
COVERAGE = ROOT / "data/canonical/kokkoritsu/coverage.csv"
OPS = ROOT / "data/operations/coverage_reaudit_2027.csv"
KAWAI = ROOT / "data/operations/kawai_coverage_audit_2027.csv"
QUEUE = ROOT / "data/operations/update_queue.csv"
PILOT = ROOT / "data/operations/candidate_fields_pilot_2027.csv"
CORR = ROOT / "data/operations/canonical_corrections_2027.jsonl"

PAGE = "https://juken.hit-u.ac.jp/admission/info/guidelines/"
GUIDE = "https://juken.hit-u.ac.jp/admission/info/guidelines/files/R9senbatsu.pdf"

PFI_UNITS = [
    ("COM", "商学部", "経営学科・商学科", "商学・経営"),
    ("ECON", "経済学部", "経済学科", "経済学"),
    ("LAW", "法学部", "法律学科", "法学"),
    ("SOC", "社会学部", "社会学科", "社会学"),
]

REC_IDS = {
    "HIT-2027-REC-COM",
    "HIT-2027-REC-ECON",
    "HIT-2027-REC-LAW",
    "HIT-2027-REC-SOC",
    "HIT-2027-REC-SDS",
}
FOREIGN_IDS = {
    "HIT-2027-FOREIGN-COM",
    "HIT-2027-FOREIGN-ECON",
    "HIT-2027-FOREIGN-LAW",
    "HIT-2027-FOREIGN-SOC",
}


def read(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), [dict(row) for row in reader]


def write(path: Path, header: list[str], rows: list[dict[str, str]]):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=header, lineterminator="\n", extrasaction="raise"
        )
        writer.writeheader()
        writer.writerows(rows)


def blank(header: list[str]):
    return {key: "" for key in header}


def upsert(rows: list[dict[str, str]], key: str, row: dict[str, str]):
    for i, old in enumerate(rows):
        if old.get(key) == row.get(key):
            rows[i] = row
            return
    rows.append(row)


def pfi_row(header: list[str], code: str, faculty: str, dept: str, field: str):
    row = blank(header)
    row.update({
        "record_id": f"HIT-2027-PFI-{code}",
        "admission_year": "2027",
        "institution_type": "国立",
        "university": "一橋大学",
        "prefecture": "東京都",
        "academic_field": field,
        "stem_flag": "False",
        "faculty_school": faculty,
        "department": dept,
        "selection_category": "特別選抜",
        "selection_name": "私費外国人留学生選抜",
        "slot_type": dept,
        "international_baccalaureate_flag": "No",
        "private_foreign_student_flag": "Yes",
        "returnee_flag": "No",
        "regional_quota_flag": "No",
        "adult_selection_flag": "No",
        "capacity": "若干名",
        "school_recommendation_required": "No",
        "exclusive_enrollment_status": "不明",
        "exclusive_enrollment": "2027年度入学者選抜要項には、合格時の入学確約又は他大学との併願可を明示する記載を確認できない。9月25日公開の詳細募集要項を追加精査中。",
        "eligibility_graduation": "日本国籍を有せず日本国の永住許可を取得していない者で、外国の12年課程修了・修了見込み又はIB等の所定大学入学資格を満たし、指定期間のTOEFL iBT及び日本留学試験の要件を満たす者。",
        "gpa_requirement": "2027年度入学者選抜要項に数値による評定要件の明示なし。",
        "english_requirement": "2025-02-01～2026-10-31にTOEFL iBTを受験し、2026-01-20以前の試験は48点以上、2026-01-21以降の試験はバンドスコア3以上。Official Score Report(s)をETSから一橋大学へ直送。",
        "subject_prerequisites": "日本留学試験（日本語〔記述を除く〕、総合科目、数学コース1）を2025年度第1回～2026年度第1回に受験し、3科目合計680点以上。",
        "common_test_required": "No",
        "common_test_usage": "大学入学共通テストは課さない。日本留学試験、TOEFL iBT、本学学力試験を利用。",
        "research_activity_level": "not_specified",
        "research_requirement_required": "No",
        "academic_record_required": "Unknown",
        "academic_record_detail": "2027年度私費外国人留学生選抜募集要項は2026-09-25公開済。成績関係書類の正式名称・提出条件は詳細募集要項の追加精査で確定する。",
        "documents_summary": "提出書類等を選抜に使用。正式な提出書類一覧は2026-09-25公開の私費外国人留学生選抜募集要項を追加精査中。",
        "selection_process": "日本留学試験・TOEFL iBTの成績、本学学力試験（日本語）及び提出書類等により総合判定。",
        "selection_document_review": "Yes",
        "selection_interview": "No",
        "selection_oral_exam": "No",
        "selection_presentation": "No",
        "selection_essay": "No",
        "selection_written_exam": "Yes",
        "selection_practical": "No",
        "selection_group_discussion": "No",
        "selection_aptitude_test": "No",
        "selection_common_test": "No",
        "written_exam_detail": "本学学力試験は日本語。社会・文化に関する論文等を示し、日本語の作文力・読解力等をみる。2027年度入学者選抜要項の本学配点は580点。",
        "selection_method_detail": "2027年度入学者選抜要項では、日本留学試験1000点換算＋TOEFL 420点換算＋本学日本語580点の計2000点を示し、提出書類等と合わせて総合判定。",
        "application_start": "2026-11-09",
        "application_end": "2026-11-18",
        "second_stage_start": "2027-02-01",
        "second_stage_end": "2027-02-01",
        "final_result_date": "2027-03-01",
        "source_status": "2027年度入学者選抜要項確認済・私費外国人留学生選抜募集要項2026-09-25公開済（詳細再監査中）",
        "detail_completeness": "partial（2027年度入学者選抜要項で募集単位・出願資格・主要選抜方法・日程を確認。詳細募集要項の提出書類等を追加精査中）",
        "verification_grade": "A",
        "verified_on": "2026-09-28",
        "source_url": PAGE,
        "schedule_url": GUIDE,
        "guideline_url": GUIDE,
        "notes": "2026-09-28 Coverage再監査で未収録を確認し追加。2027年度入学者選抜要項では商・経済・法・社会の4学部で実施、各若干名。ソーシャル・データサイエンス学部では実施しない。詳細募集要項は9月25日公開済で追加精査をUpdateQueue管理。",
        "information_year": "2027",
        "publication_status": "2027年度入学者選抜要項・私費外国人留学生選抜募集要項公開済",
        "fallback_previous_year": "No",
    })
    return row


def update_existing_hitotsubashi(rows: list[dict[str, str]]):
    for row in rows:
        rid = row.get("record_id", "")
        if rid in REC_IDS:
            row.update({
                "source_status": "2027年度入学者選抜要項確認済・学校推薦型選抜募集要項2026-09-25公開済（詳細再監査中）",
                "detail_completeness": "partial（2027年度主要項目確認済・9月25日公開の学校推薦型選抜募集要項を追加精査中）",
                "verified_on": "2026-09-28",
                "source_url": PAGE,
                "schedule_url": GUIDE,
                "guideline_url": GUIDE,
                "publication_status": "2027年度入学者選抜要項・学校推薦型選抜募集要項公開済",
                "current_year_release_expected": "",
                "notes": "2027年度入学者選抜要項から学部別に抽出済。2026-09-25に学校推薦型選抜募集要項が公開されたため、推薦人数上限・提出書類細則・入学手続等の追加精査を継続。",
                "fallback_note": "",
            })
        elif rid in FOREIGN_IDS:
            row.update({
                "returnee_flag": "Yes",
                "selection_document_review": "Yes",
                "written_exam_detail": "第1次選抜：英語（聞き取り・書き取りなし）100点＋小論文100点。第2次選抜：第1次成績に面接100点を加え総合判定。",
                "application_start": "2026-11-20",
                "application_end": "2026-12-02",
                "first_stage_result_date": "2027-03-01",
                "second_stage_start": "2027-03-03",
                "second_stage_end": "2027-03-03",
                "final_result_date": "2027-03-10",
                "source_status": "2027年度入学者選抜要項確認済・外国学校出身者選抜募集要項2026-09-25公開済（詳細再監査中）",
                "detail_completeness": "partial（2027年度入学者選抜要項で4学部・募集人員・出願資格・選抜方法・日程を確認。詳細募集要項の提出書類等を追加精査中）",
                "verification_grade": "A",
                "verified_on": "2026-09-28",
                "source_url": PAGE,
                "schedule_url": GUIDE,
                "guideline_url": GUIDE,
                "notes": "2026-09-28再監査。2027年度入学者選抜要項で商・経済・法・社会の4学部、各5人以内、共通テスト免除、第1次（英語・小論文＋書類審査）・第2次面接及び日程を確認。専用の外国学校出身者選抜のためreturnee_flag=Yesへ補正。詳細募集要項は9月25日公開済で追加精査中。",
                "publication_status": "2027年度入学者選抜要項・外国学校出身者選抜募集要項公開済",
                "current_year_release_expected": "",
                "fallback_note": "",
            })


def main():
    header, rows = read(MASTER)
    rows = [
        row for row in rows
        if not (
            row.get("university") == "一橋大学"
            and row.get("record_id", "").startswith("HIT-2027-PFI-")
        )
    ]
    before = len(rows)
    update_existing_hitotsubashi(rows)
    additions = [pfi_row(header, *unit) for unit in PFI_UNITS]
    rows.extend(additions)
    write(MASTER, header, rows)

    h2, cov = read(COVERAGE)
    c = next(row for row in cov if row["university"] == "一橋大学")
    c.update({
        "research_status": "Master反映済・2027詳細募集要項再監査中",
        "master_rows": "13",
        "current_year_status": "2027年度情報を反映（学校推薦型・外国学校出身者・私費外国人留学生の詳細募集要項は9月25日公開済、細部精査継続）",
        "fallback_status": "不要（現行情報あり）",
        "checked_on": "2026-09-28",
        "official_source_url": PAGE,
        "notes": "2026-09-28 Coverage再監査：公式2027体系とMasterを再照合。学校推薦型5＋外国学校出身者4＋私費外国人留学生4＝13募集単位。私費外国人留学生4行を新規追加し、外国学校出身者4行をreturnee_flag=Yesへ補正。SDSは学校推薦型のみで、外国学校出身者・私費外国人留学生は実施なし。3詳細募集要項は9月25日公開済のため、提出書類・入学手続等をUpdateQueueで追加精査。",
    })
    write(COVERAGE, h2, cov)

    h3, ops = read(OPS)
    o = next(
        row for row in ops
        if row["source_dataset"] == "kokkoritsu" and row["university"] == "一橋大学"
    )
    o.update({
        "reaudit_status": "追加確認待ち",
        "official_system_checked": "実施済",
        "capacity_table_checked": "実施済",
        "schedule_checked": "実施済",
        "guideline_index_checked": "実施済",
        "master_compared": "実施済",
        "kawai_crosscheck": "実施済",
        "missing_candidate_count": "0",
        "ambiguous_candidate_count": "0",
        "obsolete_candidate_count": "0",
        "update_queue_open_count": "3",
        "last_audited_on": "2026-09-28",
        "notes": "2027公式体系・入学者選抜要項・募集要項一覧とMasterを再照合。従来9行に未収録の私費外国人留学生4募集単位を追加して13行。外国学校出身者4行は専用選抜のためreturnee_flag=Yesへ補正。学校推薦型5行は維持。Kei-Net 2027推薦5学部は照合済でmissingなし。9月25日公開の3詳細募集要項について、提出書類・推薦人数・入学手続等の深掘りを継続。",
    })
    write(OPS, h3, ops)

    h4, kawai = read(KAWAI)
    k = next(
        row for row in kawai
        if row["source_dataset"] == "kokkoritsu" and row["university"] == "一橋大学"
    )
    k.update({
        "kawai_crosscheck_status": "照合済・欠落候補なし",
        "missing_candidate_status": "なし（Kei-Net学校推薦型掲載範囲）",
        "official_confirmation_status": "確認済",
        "last_checked_on": "2026-09-28",
        "notes": "Kei-Net 2027学校推薦型5学部とMaster学校推薦型5行が対応しmissing candidateなし。外国学校出身者4行・私費外国人留学生4行はKei-Net推薦/総合型DB対象外のため、一橋大学公式2027入学者選抜要項・募集要項一覧でCoverage確認。",
    })
    write(KAWAI, h4, kawai)

    h5, queue = read(QUEUE)
    q_foreign = next(row for row in queue if row.get("queue_id") == "UQ-2027-0003")
    q_foreign.update({
        "publication_status": "公開済",
        "release_expected_text": "2026年9月下旬頃",
        "release_expected_from": "2026-09-21",
        "release_expected_to": "2026-09-30",
        "release_schedule_url": PAGE,
        "last_checked_on": "2026-09-28",
        "next_check_on": "",
        "actual_release_on": "2026-09-25",
        "action_status": "更新中",
        "notes": "2026-09-25公開済。2027入学者選抜要項で4募集単位・日程・主要選抜方法を再確認し、returnee_flag=Yesへ補正済。詳細募集要項から提出書類、成績関係書類、入学手続期限等を追加精査中。",
    })

    def queue_row(qid: str, selection: str, note: str):
        r = blank(h5)
        r.update({
            "queue_id": qid,
            "institution_type": "国立",
            "university": "一橋大学",
            "selection_name": selection,
            "document_type": "募集要項",
            "publication_status": "公開済",
            "release_expected_text": "2026年9月下旬頃",
            "release_expected_from": "2026-09-21",
            "release_expected_to": "2026-09-30",
            "release_schedule_url": PAGE,
            "last_checked_on": "2026-09-28",
            "actual_release_on": "2026-09-25",
            "action_status": "更新中",
            "notes": note,
        })
        return r

    upsert(queue, "queue_id", queue_row(
        "UQ-2027-0043",
        "学校推薦型選抜",
        "2026-09-25公開済。既存5学部の主要条件は2027入学者選抜要項で反映済。詳細募集要項から学校推薦人数上限、提出書類細則、WEB出願、入学手続期限等を追加精査する。",
    ))
    upsert(queue, "queue_id", queue_row(
        "UQ-2027-0044",
        "私費外国人留学生選抜",
        "2026-09-25公開済。2027入学者選抜要項で商・経済・法・社会4募集単位、各若干名、TOEFL/EJU要件、学力試験・日程をMasterへpartial反映済。詳細募集要項から提出書類、成績関係書類、入学手続期限等を追加精査する。",
    ))
    write(QUEUE, h5, queue)

    h6, pilot = read(PILOT)
    def pilot_row(rid: str, faculty: str, dept: str, selection: str, status: str, grad_detail: str, guide_note: str):
        p = blank(h6)
        p.update({
            "source_dataset": "kokkoritsu",
            "record_id": rid,
            "university": "一橋大学",
            "faculty_school": faculty,
            "department": dept,
            "selection_name": selection,
            "slot_type": dept,
            "enrollment_procedure_deadline": "",
            "enrollment_procedure_detail": "2026-09-25公開の詳細募集要項で追加確認中。",
            "graduation_eligibility_status": status,
            "years_since_graduation_max": "",
            "graduation_eligibility_detail": grad_detail,
            "regional_requirement_status": "No",
            "regional_requirement_detail": "2027年度入学者選抜要項では都道府県居住・高校所在地等による地域枠条件なし。外国課程等の出願資格は地域枠とは別に扱う。",
            "gender_requirement": "制限なし",
            "gender_requirement_detail": "2027年度入学者選抜要項に性別条件の明示なし。",
            "guideline_url": GUIDE,
            "reviewed_on": "2026-09-28",
            "pilot_status": "pilot",
            "notes": guide_note,
        })
        return p

    upsert(pilot, "record_id", pilot_row(
        "HIT-2027-REC-COM",
        "商学部",
        "経営学科・商学科",
        "学校推薦型選抜",
        "既卒可",
        "高等学校又は中等教育学校の卒業者及び2027年3月卒業見込みの者を対象とする。",
        "学校推薦型代表。入学手続期限は詳細募集要項の追加精査で確定する。",
    ))
    upsert(pilot, "record_id", pilot_row(
        "HIT-2027-PFI-COM",
        "商学部",
        "経営学科・商学科",
        "私費外国人留学生選抜",
        "その他",
        "日本国籍を有せず日本国の永住許可を取得していない者で、外国12年課程修了・修了見込み又は所定の国際資格等を満たす者。",
        "私費外国人留学生代表。2027選抜要項で主要出願資格・日程確認済。",
    ))
    write(PILOT, h6, pilot)

    items = [
        json.loads(line)
        for line in CORR.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    cc = {
        "correction_id": "CC-2027-0008",
        "dataset": "kokkoritsu",
        "university": "一橋大学",
        "detected_on": "2026-09-28",
        "status": "applied_partial_pending_detail",
        "reason": "Coverage re-audit under the expanded special-selection scope found the 2027 private-foreign selection absent from canonical Master and the dedicated foreign-school selection missing its returnee flag.",
        "existing_master_rows": 9,
        "missing_selection_groups": [
            {
                "selection_name": "私費外国人留学生選抜",
                "confirmed_units": 4,
                "grain": "商学部 / 経済学部 / 法学部 / 社会学部",
                "apply_status": "applied_partial",
                "update_queue_id": "UQ-2027-0044",
            }
        ],
        "flag_corrections": [
            {
                "selection_name": "外国学校出身者選抜",
                "affected_units": 4,
                "field": "returnee_flag",
                "from": "No",
                "to": "Yes",
            }
        ],
        "confirmed_missing_units_total": 4,
        "applied_master_rows": 4,
        "current_university_master_rows": 13,
        "official_source": "2027年度一橋大学入学者選抜要項・2027年度募集要項一覧",
        "official_url": PAGE,
        "audit_note": "Private-foreign selection is explicitly offered by Commerce, Economics, Law and Social Sciences, each with a few seats; Social Data Science is not listed. The three detailed guides were published on 2026-09-25 and remain queued for field-level extraction not already present in the selection guide.",
    }
    items = [x for x in items if x.get("correction_id") != "CC-2027-0008"] + [cc]
    CORR.write_text(
        "\n".join(json.dumps(x, ensure_ascii=False, separators=(",", ":")) for x in items) + "\n",
        encoding="utf-8",
    )

    ids = [row["record_id"] for row in rows]
    hit = [row for row in rows if row.get("university") == "一橋大学"]
    assert len(rows) == before + 4
    assert len(ids) == len(set(ids))
    assert len(hit) == 13
    assert sum(row.get("private_foreign_student_flag") == "Yes" for row in hit) == 4
    assert sum(row.get("returnee_flag") == "Yes" for row in hit) == 4
    assert sum(row.get("international_baccalaureate_flag") == "Yes" for row in hit) == 0
    assert sum(row.get("regional_quota_flag") == "Yes" for row in hit) == 0
    assert sum(row.get("adult_selection_flag") == "Yes" for row in hit) == 0
    assert sum(row.get("selection_name") == "学校推薦型選抜" for row in hit) == 5
    assert sum(row.get("selection_name") == "外国学校出身者選抜" for row in hit) == 4
    assert sum(row.get("selection_name") == "私費外国人留学生選抜" for row in hit) == 4

    print(json.dumps({
        "kokkoritsu_rows_after": len(rows),
        "hitotsubashi_rows": len(hit),
        "recommendation": 5,
        "foreign_school_returnee": 4,
        "private_foreign": 4,
        "update_queue_open": 3,
        "reaudit_status": "追加確認待ち",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
