#!/usr/bin/env python3
"""Complete the 2027 Hitotsubashi detailed-guideline follow-up.

Only existing Master fields and operational ledgers are updated. Post-admission
enrollment deadlines, which have no structured field in the current Master
schema, are recorded in provenance notes without changing the schema.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = "https://juken.hit-u.ac.jp/admission/info/guidelines/"
GUIDES = {
    "学校推薦型選抜": "https://juken.hit-u.ac.jp/admission/info/guidelines/files/R9suisen_youkou.pdf",
    "外国学校出身者選抜": "https://juken.hit-u.ac.jp/admission/info/guidelines/files/R9gaikoku_youkou.pdf",
    "私費外国人留学生選抜": "https://juken.hit-u.ac.jp/admission/info/guidelines/files/R9ryuugaku_youkou.pdf",
}
DATE = "2026-09-28"


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), [dict(row) for row in reader]


def write_csv(path: Path, header: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


REC_DOCS = (
    "Web出願志願票、出身学校調査書（2026年4月以降作成・厳封）、学校長作成の"
    "推薦書（厳封）、本人作成の自己推薦書（片面3枚以内）、各学部の出願要件を"
    "満たす資格・実績の証明書類。"
)
REC_ACADEMIC = (
    "出身学校調査書を提出。出身学校長が2026年4月以降に作成し厳封する。"
    "中等教育学校は後期課程のみの調査書でも可。調査書は選考資料として扱われる。"
)
REC_CAP = (
    "2027年度学校推薦型選抜募集要項を確認した範囲では、学校あたりの推薦人数上限の"
    "記載を確認できず。数値は補わず空欄を保持する。"
)
REC_DEADLINE = "入学手続期限は2027-02-18必着。"

FOREIGN_DOCS = (
    "Web出願志願票、出願資格に応じた最終出身校の卒業（修了）証明書と学業成績証明書、"
    "履歴書、海外在留歴調書、海外在留証明等。日本の高校在学歴がある者は当該期間の調査書。"
    "IB・Abitur・Baccalaureate・GCE等の資格経路では該当資格証書・成績評価証明書を提出。"
    "国籍・永住資格証明等は該当者に必要。"
)
FOREIGN_ACADEMIC = (
    "学業成績証明書または出願資格に応じた成績評価証明書を提出。日本の高校（中等教育学校"
    "後期課程を含む）に在学していた場合は、その在学期間の調査書も必要。資格経路ごとに"
    "証明書の種類・原本要件が異なる。"
)
FOREIGN_DEADLINE = "郵送による入学手続期限は2027-03-15必着。"

PFI_DOCS = (
    "Web出願志願票、資格経路に応じた卒業（修了）証明書・学業成績証明書または資格証書・"
    "成績評価証明書、TOEFL iBT公式スコア（ETSから大学へ直送）、日本留学試験の成績確認書、"
    "所定履歴書、在留資格確認書類。日本国内の日本語教育機関に在籍し留学資格を持つ者は"
    "出席率証明書も提出。"
)
PFI_ACADEMIC = (
    "出願資格に応じて最終出身校の学業成績証明書、IB等の資格証書・成績評価証明書を提出。"
    "TOEFL iBT公式スコアと日本留学試験成績確認書も必要。証明書の原本要件は資格経路で異なる。"
)
PFI_DEADLINE = (
    "郵送による入学手続期限は2027-03-08必着。合格通知書送付先が未登録の場合の来学手続は"
    "2027-03-04、03-05。"
)


def update_master() -> int:
    path = ROOT / "data/canonical/kokkoritsu/master.csv"
    header, rows = read_csv(path)
    hit = [r for r in rows if r.get("university") == "一橋大学"]
    if len(hit) != 13:
        raise SystemExit(f"Expected 13 Hitotsubashi rows; found {len(hit)}")
    if {r["selection_name"] for r in hit} != set(GUIDES):
        raise SystemExit("Hitotsubashi selection groups differ from the reviewed set")

    for row in hit:
        selection = row["selection_name"]
        guide = GUIDES[selection]
        row.update({
            "verified_on": DATE,
            "source_url": PAGE,
            "schedule_url": guide,
            "guideline_url": guide,
            "publication_status": "2027年度選抜要項・詳細募集要項公開済",
            "current_year_release_expected": "",
            "source_status": "2027年度詳細募集要項確認済",
            "detail_completeness": "complete（2027年度詳細募集要項まで確認済）",
            "verification_grade": "A",
        })
        if selection == "学校推薦型選抜":
            row["school_nomination_limit_rule"] = REC_CAP
            row["academic_record_required"] = "Yes"
            row["academic_record_type"] = "調査書"
            row["academic_record_detail"] = REC_ACADEMIC
            row["documents_summary"] = REC_DOCS
            method_detail = row.get("selection_method_detail", "")
            method_detail = method_detail.replace(
                "詳細募集要項公開前のため、出願手続・書式・推薦人数上限等は未確定。", ""
            ).rstrip("。")
            row["selection_method_detail"] = (
                method_detail + "。提出書類は" + REC_DOCS + REC_DEADLINE
            )
            row["notes"] = (
                f"2026-09-28詳細再監査。公式2027学校推薦型選抜募集要項：{guide}。"
                f"{REC_CAP} {REC_ACADEMIC} {REC_DEADLINE}"
            )
        elif selection == "外国学校出身者選抜":
            row["academic_record_required"] = "Yes"
            row["academic_record_type"] = "学業成績証明書、該当者は調査書"
            row["academic_record_detail"] = FOREIGN_ACADEMIC
            row["documents_summary"] = FOREIGN_DOCS
            row["selection_method_detail"] = (
                row.get("selection_method_detail", "").rstrip("。")
                + "。提出書類："
                + FOREIGN_DOCS
                + FOREIGN_DEADLINE
            )
            row["notes"] = (
                f"2026-09-28詳細再監査。公式2027外国学校出身者選抜募集要項：{guide}。"
                f"{FOREIGN_ACADEMIC} {FOREIGN_DEADLINE}"
            )
        else:
            row["academic_record_required"] = "Yes"
            row["academic_record_type"] = "学業成績証明書または資格別成績評価証明書"
            row["academic_record_detail"] = PFI_ACADEMIC
            row["documents_summary"] = PFI_DOCS
            row["selection_method_detail"] = (
                row.get("selection_method_detail", "").rstrip("。")
                + "。提出書類："
                + PFI_DOCS
                + PFI_DEADLINE
            )
            row["notes"] = (
                f"2026-09-28詳細再監査。公式2027私費外国人留学生選抜募集要項：{guide}。"
                f"{PFI_ACADEMIC} {PFI_DEADLINE}"
            )

    write_csv(path, header, rows)
    return len(hit)


def update_coverage() -> None:
    path = ROOT / "data/canonical/kokkoritsu/coverage.csv"
    header, rows = read_csv(path)
    row = next(r for r in rows if r.get("university") == "一橋大学")
    row.update({
        "research_status": "Master反映済・追加項目再監査済",
        "master_rows": "13",
        "current_year_status": "2027年度の学校推薦型5・外国学校出身者4・私費外国人留学生4募集単位を詳細要項まで再監査済",
        "fallback_status": "不要（2027年度公式詳細要項確認済）",
        "checked_on": DATE,
        "official_source_url": PAGE,
        "notes": (
            "2027年度公式入試体系・募集人員・日程・3種の詳細募集要項をMaster全13行と照合。"
            "提出書類・成績関係書類・推薦人数上限・入学手続期限を反映。"
            "学校推薦型の学校別推薦人数上限は公式要項に記載を確認できず、数値は空欄のまま。"
            "Kei-Net 2027学校推薦型5学部とのクロスチェックで欠落候補なし。"
        ),
    })
    write_csv(path, header, rows)


def update_operations() -> None:
    path = ROOT / "data/operations/coverage_reaudit_2027.csv"
    header, rows = read_csv(path)
    row = next(r for r in rows if r.get("source_dataset") == "kokkoritsu" and r.get("university") == "一橋大学")
    row.update({
        "reaudit_status": "再監査済",
        "update_queue_open_count": "0",
        "last_audited_on": DATE,
        "notes": (
            "公式2027入試体系・募集人員・日程・募集要項一覧を確認し、Master13行と照合済。"
            "3詳細要項から提出書類、成績関係書類、推薦人数条件、入学手続期限まで反映。"
            "Kei-Net推薦5学部は照合済、欠落候補なし。"
        ),
    })
    write_csv(path, header, rows)

    path = ROOT / "data/operations/update_queue.csv"
    header, rows = read_csv(path)
    target_ids = {"UQ-2027-0003", "UQ-2027-0043", "UQ-2027-0044"}
    found = set()
    for row in rows:
        if row.get("queue_id") not in target_ids:
            continue
        found.add(row["queue_id"])
        row.update({
            "last_checked_on": DATE,
            "next_check_on": "",
            "action_status": "完了",
            "notes": (
                "2026-09-25公開の2027年度詳細募集要項を確認し、提出書類・成績関係書類・"
                "選抜日程・入学手続期限を全該当Master行へ反映済。"
            ),
        })
    if found != target_ids:
        raise SystemExit(f"Hitotsubashi queue entries missing: {sorted(target_ids-found)}")
    write_csv(path, header, rows)

    path = ROOT / "data/operations/canonical_corrections_2027.jsonl"
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    correction = next(r for r in records if r.get("correction_id") == "CC-2027-0008")
    correction["status"] = "applied_complete"
    correction["audit_note"] = (
        "私費外国人留学生4行を含むMaster13行を2027年度詳細募集要項まで再監査。"
        "外国学校出身者4行のreturnee_flag補正を含む全確認済み項目を反映。"
        "学校推薦型・外国学校出身者・私費外国人留学生の提出書類、成績関係書類、"
        "日程、入学手続期限を記録。学校別推薦人数上限は明記を確認できず、数値を補完していない。"
    )
    path.write_text("".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n" for r in records), encoding="utf-8")


def main() -> None:
    count = update_master()
    update_coverage()
    update_operations()
    print(f"Completed official detail review for Hitotsubashi: {count} Master rows")


if __name__ == "__main__":
    main()
