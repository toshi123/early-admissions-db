# 室蘭工業大学 2027年度再監査記録（募集単位確認）

- 確認日：2026-09-28
- 対象：理工学部の早期選抜
- 状態：公式体系・募集単位照合済。15件のCanonical詳細反映は未着手。

## 公式資料

- [学生募集要項一覧](https://muroran-it.ac.jp/entrance/admission/exam/uee/)（ページ更新 2026-09-03）
- [令和9年度入学試験概要](https://muroran-it.ac.jp/uploads/sites/6/2026/06/R09nyugakusyagaiyou.pdf)
- [令和9年度総合型選抜要項](https://muroran-it.ac.jp/uploads/sites/6/2026/08/R9_sougo_bosyu.pdf)
- [令和9年度総合型選抜（帰国子女・社会人・企業推薦型）要項](https://muroran-it.ac.jp/uploads/sites/6/2026/08/2027tokubetsu-1.pdf)
- [2027年度総合型選抜（私費外国人留学生）要項](https://muroran-it.ac.jp/uploads/sites/6/2026/08/2027shihiyoukou-1.pdf)
- [令和9年度学校推薦型選抜要項](https://muroran-it.ac.jp/uploads/sites/6/2026/09/R9gakkousuisennyoukou.pdf)
- [2027年度中国引揚等子女募集停止予告](https://muroran-it.ac.jp/entrance/admission/exam/uee/)

## 募集単位 inventory

| 方式 | 確認単位 | Master照合 |
|---|---:|---|
| 学校推薦型（昼間） | 2学科 | 既収録2 |
| 総合型I（昼間） | 2学科×一般/女子枠 | missing candidate 4 |
| 総合型II（昼間） | 2学科×一般/女子枠 | missing candidate 4 |
| 総合型（夜間主） | 1学科 | missing candidate 1 |
| 総合型（帰国子女） | 2学科 | missing candidate 2 |
| 総合型（社会人・夜間主） | 1学科 | missing candidate 1 |
| 総合型（企業推薦型・夜間主） | 1学科 | missing candidate 1 |
| 総合型（私費外国人留学生・昼間） | 2学科 | missing candidate 2 |
| **合計** | **17** | **2 matched / 15 missing candidates**

総合型I/IIでは公式要項が女子枠志願者について希望による一般枠併願を認めており、枠ごとに募集人員・判定を設けるため、各学科の一般枠と女子枠を別selection slotとして数えた。コースは学科内の出願先ではなく、入学後のコース分属に関する希望として扱い、行をコース別に分割しない。推薦要項も出願後の志望学科変更を認めず、志望理由書で「目指すコース」を記載するため、コース単位ではなく学科単位とした。

2027年度の中国引揚等子女選抜は大学公式の募集停止予告があるため候補に含めない。

## 特殊選抜フラグの方針

- 私費外国人留学生2件：`private_foreign_student_flag=Yes`。
- 帰国子女2件：`returnee_flag=Yes`。
- 社会人枠1件：`adult_selection_flag=Yes`。企業推薦型は年齢・職歴要件だけで社会人選抜とは扱わず、Schema定義に沿って同フラグを推定しない。
- IB・地域枠は選抜名・募集枠に該当する根拠がなくNo。
- 総合型I/IIの女子枠は、現在の5特殊フラグのどれにも該当しない。

## 未完了

15候補について募集要項本文から、出願資格、評定/英語/EJU、成績書類、提出書類、選考方法、日程、入学手続期限をMaster既存2件と同じ粒度で照合する。その確定後にCanonical、Coverage、UpdateQueue、correction ledger、pilotを更新し、validationからproduction acceptanceまで実行する。現時点ではCanonicalや派生成果物を変更していない。
