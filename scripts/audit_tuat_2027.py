#!/usr/bin/env python3
from __future__ import annotations
import csv, json, re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MASTER=ROOT/"data/canonical/kokkoritsu/master.csv"
COVERAGE=ROOT/"data/canonical/kokkoritsu/coverage.csv"
OPS=ROOT/"data/operations/coverage_reaudit_2027.csv"
KAWAI=ROOT/"data/operations/kawai_coverage_audit_2027.csv"
QUEUE=ROOT/"data/operations/update_queue.csv"
PILOT=ROOT/"data/operations/candidate_fields_pilot_2027.csv"
CORR=ROOT/"data/operations/canonical_corrections_2027.jsonl"
SRC="https://www.tuat.ac.jp/admission/nyushi_gakubu/youkou/"
SEL="https://www.tuat.ac.jp/documents/tuat/admission/nyushi_gakubu/youkou/r9_senbatuyoukou.pdf"

def read(path):
    with path.open("r",encoding="utf-8-sig",newline="") as f:
        r=csv.DictReader(f); return list(r.fieldnames or []), [dict(x) for x in r]
def write(path,h,rows):
    with path.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=h,lineterminator="\n",extrasaction="raise"); w.writeheader(); w.writerows(rows)
def blank(h): return {k:"" for k in h}

AG=[
 ("BIOPROD","生物生産学科","農学"),("APBIO","応用生物科学科","農学"),
 ("ENV","環境資源科学科","環境・農学"),("REGION","地域生態システム学科","環境・農学"),
 ("VET","共同獣医学科","獣医")
]
EN=[
 ("BIO","生命工学科","生命・バイオ"),("BIOMED","生体医用システム工学科","工学"),
 ("APCHEM","応用化学科","化学・材料"),("CHEMPHYS","化学物理工学科","工学"),
 ("MECH","機械システム工学科","工学"),("INFO","知能情報システム工学科","情報")
]

def base(h,rid,faculty,dept,field,name,flag):
    r=blank(h)
    r.update({
      "record_id":rid,"admission_year":"2027","institution_type":"国立","university":"東京農工大学","prefecture":"東京都",
      "academic_field":field,"stem_flag":"True","faculty_school":faculty,"department":dept,
      "selection_category":"特別選抜","selection_name":name,"slot_type":name,"capacity":"若干名",
      "international_baccalaureate_flag":"No","private_foreign_student_flag":"No","returnee_flag":"No","regional_quota_flag":"No",
      "school_recommendation_required":"No","exclusive_enrollment_status":"不明",
      "exclusive_enrollment":"2027年度公式資料に合格時の入学確約・併願可の明示を確認できないため不明。",
      "common_test_required":"No","common_test_usage":"大学入学共通テストを免除。",
      "research_activity_level":"not_specified","research_requirement_required":"No",
      "academic_record_required":"Yes","selection_document_review":"Yes","selection_interview":"Yes",
      "selection_oral_exam":"Unknown","selection_presentation":"No","selection_essay":"No","selection_written_exam":"Yes",
      "selection_practical":"No","selection_group_discussion":"No","selection_aptitude_test":"No","selection_common_test":"No",
      "source_status":"2027年度公式入学者選抜要項確認済・特別選抜学生募集要項詳細再確認待ち",
      "detail_completeness":"partial（特別選抜学生募集要項詳細再確認待ち）","verification_grade":"A","verified_on":"2026-09-28",
      "source_url":SRC,"schedule_url":SRC,"guideline_url":SEL,
      "information_year":"2027","publication_status":"2027年度公式情報","fallback_previous_year":"No",
      "notes":"2026-09-28 Coverage再監査で2027年度公式入学者選抜体系から新規収録。特別選抜学生募集要項は2026-08-28公表済みで、詳細項目はUpdateQueueで再精査。"
    })
    r[flag]="Yes"
    return r

def social(h,code,dept,field):
    r=base(h,f"TUAT-2027-SOC-AG-{code}","農学部",dept,field,"特別選抜（社会人入試）","international_baccalaureate_flag")
    r["international_baccalaureate_flag"]="No"
    r.update({
      "eligibility_graduation":"2027年3月31日までに満23歳に達し、社会人としての経験を通算5年以上有し、大学入学資格を有する者。",
      "gpa_requirement":"数値による評定要件の明示なし。","english_requirement":"外部英語資格要件の明示なし。",
      "subject_prerequisites":"満23歳以上かつ社会人経験通算5年以上等、社会人入試の出願要件を満たすこと。",
      "documents_summary":"志望理由書、調査書等。特別選抜学生募集要項で詳細再確認。",
      "selection_process":"学力検査、面接、志望理由書、調査書等を総合して判定。大学入学共通テストは免除。",
      "application_start":"2027-01-14","application_end":"2027-01-20","second_stage_start":"2027-02-25","second_stage_end":"2027-02-26","final_result_date":"2027-03-06"
    })
    return r

def foreign(h,faculty,code,dept,field):
    r=base(h,f"TUAT-2027-FOR-{'AG' if faculty=='農学部' else 'EN'}-{code}",faculty,dept,field,"特別選抜（私費外国人留学生入試）","private_foreign_student_flag")
    r.update({
      "eligibility_graduation":"日本国籍を有しない者（日本国永住許可を受けている者を除く）で、外国における12年の学校教育課程修了等の大学所定資格を満たす者。",
      "gpa_requirement":"数値による評定要件の明示なし。",
      "english_requirement":"TOEIC L&R 500点以上又はTOEFL iBT 52点以上。",
      "subject_prerequisites":"2026年度日本留学試験の学科指定教科・科目を受験し、所定の成績基準を満たすこと。",
      "documents_summary":"日本留学試験成績、英語資格証明、出願資格関係書類等。特別選抜学生募集要項で詳細再確認。",
      "selection_process":"本学面接、日本留学試験成績、各種証明書・出願書類を総合して判定。大学入学共通テストは免除。",
      "selection_written_exam":"No",
      "application_start":"2027-01-15","application_end":"2027-01-25","second_stage_start":"2027-02-26","second_stage_end":"2027-02-26","final_result_date":"2027-03-06"
    })
    return r

def upsert(rows,key,row):
    for i,x in enumerate(rows):
        if x.get(key)==row.get(key): rows[i]=row; return
    rows.append(row)

def main():
    h,rows=read(MASTER)
    rows=[r for r in rows if not (r.get("university")=="東京農工大学" and re.match(r"^TUAT-2027-(?:SOC|FOR)-",r.get("record_id","")))]
    new=[social(h,*x) for x in AG[:4]]
    new += [foreign(h,"農学部",*x) for x in AG]
    new += [foreign(h,"工学部",*x) for x in EN]
    rows.extend(new)
    write(MASTER,h,rows)

    h2,cov=read(COVERAGE); r=next(x for x in cov if x["university"]=="東京農工大学")
    r.update({"research_status":"Master反映済・特別選抜詳細再監査待ち","master_rows":"33","current_year_status":"2027年度情報を反映","checked_on":"2026-09-28","official_source_url":SRC,
      "notes":"2026-09-28 Coverage再監査：既存18行に社会人4＋私費外国人留学生11を追加し計33行。特別選抜学生募集要項は8/28公表済みで詳細再精査をUpdateQueueへ登録。"})
    write(COVERAGE,h2,cov)

    h3,ops=read(OPS); r=next(x for x in ops if x["source_dataset"]=="kokkoritsu" and x["university"]=="東京農工大学")
    r.update({"reaudit_status":"追加確認待ち","official_system_checked":"実施済","capacity_table_checked":"実施済","schedule_checked":"実施済","guideline_index_checked":"実施済","master_compared":"実施済","kawai_crosscheck":"実施済","missing_candidate_count":"0","ambiguous_candidate_count":"0","obsolete_candidate_count":"0","update_queue_open_count":"1","last_audited_on":"2026-09-28",
      "notes":"2027公式体系とMasterを再照合。既存18行に社会人4＋私費外国人留学生11を追加し33行。Kei-Net 2027推薦・総合型は既存18行と対応し、特別選抜15行は大学公式体系から確認。特別選抜学生募集要項の詳細再精査1件をQueueへ。"})
    write(OPS,h3,ops)

    h4,ka=read(KAWAI); r=next(x for x in ka if x["source_dataset"]=="kokkoritsu" and x["university"]=="東京農工大学")
    r.update({"kawai_crosscheck_status":"実施済","missing_candidate_status":"なし（Kei-Net掲載範囲）","official_confirmation_status":"確認済","last_checked_on":"2026-09-28",
      "notes":"Kei-Net 2027推薦・総合型は既存Master18行と意味対応。大学公式2027入試体系からKei-Net掲載外の社会人4＋私費外国人留学生11を追加。"})
    write(KAWAI,h4,ka)

    h5,q=read(QUEUE)
    qr=blank(h5); qr.update({"queue_id":"UQ-2027-0037","institution_type":"国立","university":"東京農工大学","faculty_school":"農学部・工学部","selection_name":"特別選抜（社会人・私費外国人留学生）","document_type":"特別選抜学生募集要項","publication_status":"公開済","release_expected_text":"2026年8月28日公表","release_expected_from":"2026-08-28","release_expected_to":"2026-08-28","release_schedule_url":SRC,"last_checked_on":"2026-09-28","actual_release_on":"2026-08-28","action_status":"更新必要","notes":"公式ニュースで2027特別選抜学生募集要項の8/28公表を確認。構造15行はMaster反映済み。要項本文から提出書類・試験詳細等を再精査してcomplete化する。"})
    upsert(q,"queue_id",qr); write(QUEUE,h5,q)

    h6,p=read(PILOT)
    def pilot(rid,dept,sel,slot,deadline,status,yrs,detail,url):
        x=blank(h6); x.update({"source_dataset":"kokkoritsu","record_id":rid,"university":"東京農工大学","faculty_school":"工学部" if "-EN-" in rid or "SAIL" in rid else "農学部","department":dept,"selection_name":sel,"slot_type":slot,"enrollment_procedure_deadline":deadline,"graduation_eligibility_status":status,"years_since_graduation_max":yrs,"graduation_eligibility_detail":detail,"regional_requirement_status":"Unknown","regional_requirement_detail":"公式資料に地域条件の明示なし。","gender_requirement":"不明","gender_requirement_detail":"公式資料に性別条件の明示なし。","guideline_url":url,"reviewed_on":"2026-09-28","pilot_status":"pilot","notes":"東京農工大学再監査の代表募集単位。Unknownは公式資料に明示がないためでありNoとはしない。"}); return x
    for x in [
      pilot("TUAT-2027-AO-SAIL-BIO","生命工学科","総合型選抜（SAIL入試）","SAIL入試","2026-12-22","既卒可","","大学入学資格を有する者等。卒業年の一律上限なし。",SRC),
      pilot("TUAT-2027-REC-EN-BIO","生命工学科","学校推薦型選抜","学校推薦型","2027-02-17","既卒可","1","2026年3月から2027年3月までに卒業・修了又は見込み等。",SRC),
      pilot("TUAT-2027-SOC-AG-BIOPROD","生物生産学科","特別選抜（社会人入試）","特別選抜（社会人入試）","2027-03-15","その他","","満23歳以上かつ社会人経験通算5年以上等。",SRC),
      pilot("TUAT-2027-FOR-AG-BIOPROD","生物生産学科","特別選抜（私費外国人留学生入試）","特別選抜（私費外国人留学生入試）","2027-03-15","その他","","外国籍・外国12年課程修了等の所定資格。",SRC)
    ]: upsert(p,"record_id",x)
    write(PILOT,h6,p)

    items=[json.loads(x) for x in CORR.read_text(encoding="utf-8").splitlines() if x.strip()]
    cc={"correction_id":"CC-2027-0003","dataset":"kokkoritsu","university":"東京農工大学","detected_on":"2026-09-28","status":"applied_partial_pending_detail","reason":"2027 official admission system contains special selections absent from canonical Master.","existing_master_rows":18,"missing_selection_groups":[{"selection_name":"特別選抜（社会人入試）","confirmed_units":4},{"selection_name":"特別選抜（私費外国人留学生入試）","confirmed_units":11}],"confirmed_missing_units_total":15,"applied_master_rows":15,"current_university_master_rows":33,"official_source":"2027年度東京農工大学 入学者選抜要項・特別選抜学生募集要項","official_url":SRC,"update_queue_id":"UQ-2027-0037","audit_note":"15 missing application units added. Special-selection guide published 2026-08-28; deep detail extraction remains queued."}
    items=[x for x in items if x.get("correction_id")!="CC-2027-0003"]+[cc]
    CORR.write_text("\n".join(json.dumps(x,ensure_ascii=False,separators=(",",":")) for x in items)+"\n",encoding="utf-8")

    ids=[r["record_id"] for r in rows]; tuat=[r for r in rows if r["university"]=="東京農工大学"]
    assert len(rows)==4126 and len(ids)==len(set(ids)) and len(tuat)==33
    assert sum(r["private_foreign_student_flag"]=="Yes" for r in tuat)==11
    assert sum(r["international_baccalaureate_flag"]=="Yes" for r in tuat)==0
    assert sum(r["returnee_flag"]=="Yes" for r in tuat)==0
    assert sum(r["regional_quota_flag"]=="Yes" for r in tuat)==0
    print(json.dumps({"kokkoritsu_rows":len(rows),"tuat_rows":len(tuat),"new_rows":15,"private_foreign":11},ensure_ascii=False,indent=2))
if __name__=="__main__": main()
