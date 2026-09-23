const searchLink = (params = "") => `/search${params ? `?${params}` : ""}`;

const guideImage = (filename: string, alt: string, caption: string): string => `
  <figure class="guide-figure">
    <a class="guide-image-link" href="/guide/${filename}" target="_blank" rel="noopener" aria-label="${alt}を拡大して開く">
      <img src="/guide/${filename}" alt="${alt}" loading="lazy">
    </a>
    <figcaption>${caption}（画像を選ぶと拡大表示できます）</figcaption>
  </figure>`;

export function guidePage(): string {
  const nagoyaSearch = searchLink("university=%E5%90%8D%E5%8F%A4%E5%B1%8B%E5%A4%A7%E5%AD%A6");
  const academicSearch = searchLink([
    "academic_field_v2=natural_sciences",
    "academic_subfield_v2=natural_sciences%3Abiology",
    "academic_field_v2=life_sciences",
    "academic_field_v2=pharmacy",
    "common_test_required=No",
    "research_requirement_required=Yes",
    "english_requirement_status=not_required",
  ].join("&"));

  return `<main id="main" class="page guide-page">
    <header class="guide-hero">
      <p class="guide-kicker">はじめての方へ</p>
      <h1>早期入試検索サイトの使い方</h1>
      <p>大学名が決まっている場合も、学びたい分野や出願条件から探したい場合も、条件を組み合わせて候補を絞れます。</p>
      <p class="guide-important"><strong>検索結果は候補を見つけるためのものです。</strong>出願前に必ず大学の最新の募集要項・公式情報を確認してください。</p>
    </header>

    <nav class="guide-toc" aria-labelledby="guide-toc-title">
      <h2 id="guide-toc-title">目次</h2>
      <ol>
        <li><a href="#guide-university">大学名から探す</a></li>
        <li><a href="#guide-academic-field">学問分野から探す</a></li>
        <li><a href="#guide-requirements">テスト・資格などで絞る</a></li>
        <li><a href="#guide-grade">評定について</a></li>
        <li><a href="#guide-prefecture">都道府県で絞る</a></li>
        <li><a href="#guide-save-download">候補の保存とダウンロード</a></li>
      </ol>
    </nav>

    <aside class="guide-rule" aria-labelledby="guide-rule-title">
      <h2 id="guide-rule-title">条件の組み合わせ方</h2>
      <p><strong>大学名・学問分野・共通テストなど、異なる項目はAND</strong>です。同じ項目で複数選べるものは、原則として<strong>いずれかに一致（OR）</strong>します。</p>
      <p>例外として「試験内容」で面接と小論文を選ぶと、<strong>両方を実施する入試</strong>に絞ります。</p>
    </aside>

    <section id="guide-university" class="guide-section">
      <h2><span aria-hidden="true">1.</span> 大学名から探す</h2>
      <p>行きたい大学が決まっているときは、大学名の一部を入力して候補から1校を選びます。</p>
      ${guideImage("university-search-nagoya.png", "大学名欄で名古屋大学を選択した検索画面", "「名古屋」と入力すると候補が絞られ、名古屋大学を選択できます")}
      <ol class="guide-steps">
        <li>「大学名を入力」に、大学名の一部を入力します。</li>
        <li>表示された候補から大学を1校選びます。文字を入力しただけでは検索できません。</li>
        <li>必要なら学問分野など、ほかの条件も加えて「この条件で検索」を選びます。</li>
      </ol>
      <p class="guide-note">候補の表示は部分一致です。検索条件として確定した大学名は、選んだ1校と完全に一致する入試だけを対象にします。</p>
      <p><a class="button button--outline" href="${nagoyaSearch}" data-route data-start-at-top>名古屋大学から探してみる</a></p>
    </section>

    <section id="guide-academic-field" class="guide-section">
      <h2><span aria-hidden="true">2.</span> 学問分野から探す</h2>
      <p>大学名を決めていなくても、興味のある学問分野から入試を探せます。</p>
      ${guideImage("academic-field-selection.png", "理学の生物、生命科学、薬学を選択した学問分野検索画面", "理学は「生物」でさらに絞り、生命科学と薬学は分野全体を選んだ例")}
      <ol class="guide-steps">
        <li>大きな分野を選びます。複数の分野を選ぶと、そのいずれかに一致する入試を探します。</li>
        <li>「さらに絞る」が表示された分野は、小さな分類も選べます。同じ分野内で複数選ぶと、そのいずれかに一致します。</li>
        <li>大学名・都道府県・評定などを追加すると、それらもすべて満たす入試に絞られます。</li>
      </ol>
      <p class="guide-note">画面の分類は検索用です。大学が公式に使用している学科名・学問分野と同じとは限りません。</p>
    </section>

    <section id="guide-requirements" class="guide-section">
      <h2><span aria-hidden="true">3.</span> テスト・資格などで絞る</h2>
      <p>出願時に必要な実績や資格、選考で行われる試験を条件にできます。</p>
      ${guideImage("research-and-test-filters.png", "研究業績は必要、共通テストと英語資格は必要なしを選択した検索画面", "研究業績・共通テスト・英語資格の条件を追加した例")}
      <ol class="guide-steps">
        <li>「共通テスト」は指定なし・あり・なし、「研究業績」「英語資格」は指定なし・必要・必要なしから選びます。</li>
        <li>「試験内容」は、面接・口頭試問・プレゼン・小論文・筆記試験から選べます。</li>
        <li>試験内容を複数選ぶと、選んだ試験をすべて実施する入試だけが残ります。</li>
      </ol>
      <p class="guide-note">「なし」「必要なし」は、現在のデータで不要と確認できた入試です。「不明」や未記録の入試は含みません。</p>
      ${guideImage("search-results-sail.png", "指定条件の検索結果に東京農工大学生命工学科の総合型選抜SAIL入試が表示された画面", "分野と出願条件から東京農工大学のSAIL入試を見つけた例")}
      <p>この例では、理学の「生物」、生命科学、薬学のいずれかに該当し、研究業績が必要で、共通テストと英語資格が必要ない入試を検索しています。</p>
      <p><a class="button button--outline" href="${academicSearch}" data-route data-start-at-top>この条件で探してみる</a></p>
    </section>

    <section id="guide-grade" class="guide-section">
      <h2><span aria-hidden="true">4.</span> 評定について</h2>
      <p>「評定条件」は、出願資格として求められる学習成績の条件です。調査書・成績証明書を提出するかどうかとは別の情報です。</p>
      ${guideImage("grade-and-prefecture-filters.png", "評定条件と都道府県の検索項目を表示した画面", "評定条件の有無と、安全に確認できる全体評定の下限を指定できます")}
      <ol class="guide-steps">
        <li>評定を出願条件に含む入試を探すときは「評定条件あり」を選びます。</li>
        <li>自分の全体評定でさらに絞る場合は、0.0〜5.0を小数1桁までで入力します。</li>
        <li>結果の入試詳細で「評定条件（原文）」を確認します。</li>
      </ol>
      <p class="guide-note">数値検索は、安全に確認できる全体評定の下限だけを照合します。科目別条件や追加条件までは判定しないため、結果に表示されても出願資格を満たすとは限りません。「条件なし」「不明」「未記録」をまとめて扱う検索ではありません。</p>
    </section>

    <section id="guide-prefecture" class="guide-section">
      <h2><span aria-hidden="true">5.</span> 都道府県で絞る</h2>
      <p>大学の所在地から入試を探すときに使います。</p>
      <ol class="guide-steps">
        <li>「都道府県で絞り込む」を開きます。</li>
        <li>希望する都道府県を選びます。複数選ぶと、そのいずれかにある大学を探します。</li>
        <li>大学名や学問分野などを追加すると、選んだ都道府県のいずれかにあり、ほかの条件も満たす入試に絞られます。</li>
      </ol>
      <p class="guide-note">複数の都道府県が記録された大学は、該当するいずれの都道府県からも検索できます。</p>
    </section>

    <section id="guide-save-download" class="guide-section">
      <h2><span aria-hidden="true">6.</span> 候補の保存とダウンロード</h2>
      <p>気になる入試を候補リストに入れ、比較用のCSVまたはExcelファイルにまとめられます。</p>
      <div class="guide-image-grid">
        ${guideImage("save-nagoya.png", "名古屋大学生命理学科の総合型選抜を候補に追加した検索結果", "名古屋大学の入試を候補に追加")}
        ${guideImage("save-kitasato.png", "北里大学生命創薬科学科の研究成果発表型試験を候補に追加した検索結果", "北里大学の入試を候補に追加")}
      </div>
      <ol class="guide-steps">
        <li>検索結果または入試詳細で「候補に追加」を選びます。追加後は「候補から外す」に変わり、もう一度選ぶと保存を解除できます。</li>
        <li>上部の「候補リスト」を開きます。かっこ内に保存件数が表示されます。</li>
        <li>ファイルに含める入試の「出力対象」を確認し、「CSVで出力」または「Excelで出力」を選びます。</li>
      </ol>
      ${guideImage("saved-admissions.png", "名古屋大学と北里大学の2件を保存した候補リスト", "候補リストでは保存した2件を大学ごとに確認できます")}
      ${guideImage("excel-download.png", "候補リストで2件を選択しExcel出力が完了した画面", "Excelで出力すると、選択中の候補だけが1つのファイルになります")}
      <div class="guide-note">
        <p><strong>保存場所：</strong>候補はこのブラウザ・端末内に保存され、通常はブラウザを閉じても残ります。アカウントや別の端末には同期されません。ブラウザのデータ削除、プライベートブラウズ、保存を制限する設定では残らない場合があります。</p>
        <p><strong>出力内容：</strong>ファイル名は <code>early-admissions-candidates-YYYY-MM-DD.csv</code> または <code>.xlsx</code> です。大学名、学部・学科、選抜区分・名称、出願終了日、評定・英語資格・研究業績、選考方法、公式情報URLなどを含みます。Excelのシート名は「候補リスト」です。</p>
      </div>
    </section>
  </main>`;
}
