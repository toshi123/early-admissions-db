# Prefecture derived membership search contract v0.1

The unchanged unified `prefecture` value remains the display and raw exact-search source. A separate exact-value crosswalk supplies zero, one, or multiple search memberships. Frontend splitting, substring, regex, and fuzzy matching are prohibited. Unknown future raw values become `unmapped` with zero memberships.

## Frozen snapshot

- unified admissions: 5,921
- distinct non-NULL raw values: 48
- `single`: 47 raw values / 5,894 admissions
- `multi`: 1 raw value / 27 admissions
- `review_required`: 0
- `unmapped`: 0
- `not_applicable`: 0
- admission parent coverage: 5,921 / 5,921
- membership rows: 5,948
- multi raw value: `東京都・埼玉県` → `東京都`, `埼玉県`

## Frozen inputs

- taxonomy SHA-256: `d91fe231cde5698b074a8c86328dd61499aeccac32da2472e36a0e184457f906`
- crosswalk SHA-256: `46a5c032e2fc79cd2d1cbfbc33b1dac5952e70300b557fd1884558d52153481c`
- unified master SHA-256: `1df386ed99532a3dff381507978a1454d7c20113574285b2526f6ae122050279`

## URL and compatibility

The Site query parameter remains `prefecture` for compatibility, but the Site interprets it as derived membership. The structured CLI keeps `--prefecture` as raw exact matching and adds `--prefecture-membership` for derived membership. Same-field values use OR; different fields use AND.

Membership counts are generated and validated by the SQLite/Site-data build manifests. For the only multi value, both Tokyo and Saitama totals include the 27 shared admissions: Tokyo 1,010; Saitama 400.
