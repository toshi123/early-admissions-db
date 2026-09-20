# Early Admissions Search Site: DADS UI mapping v0.1

## Status and scope

This document is the design mapping for the Early Admissions Search Site UI
revision. It changes presentation and navigation behavior only. Search facts,
filter semantics, URL parameter names, result ordering, Site-data, and derived
data contracts remain unchanged.

The primary reference is the user-supplied Markdown archive for **Digital
Agency Design System beta v2.18.0**, dated 2026-09-09:

- archive: `dads-markdown-20260909.zip`
- archive SHA-256: `9373051a82547f8563660ada46be10d4b08eb0003b5ec93dc832f7c4ce8e0212`
- official documentation: <https://design.digital.go.jp/dads/>
- official HTML snippets: <https://github.com/digital-go-jp/design-system-example-components-html>
- snippet license: MIT; the required copyright and permission notice is
  preserved in [Third-party notices](third_party_notices.md)
- referenced documents: header container, horizontal menu, link text, color,
  accessibility, checkbox, radio, input text, combobox, disclosure, button,
  resource list, description list, and page navigation

Implementation details were also checked against the Digital Agency's
official vanilla HTML/CSS snippets at commit
`af8b6656c8d864a22ef444d088e5568f3416f6aa` (MIT License). The Site does not
copy the whole snippet package or add a runtime dependency. It reuses the
relevant visual and accessibility rules in the existing vanilla TypeScript and
CSS architecture. The repository retains the upstream MIT notice and makes no
claim of Digital Agency endorsement.

## Component audit and implementation decision

| Existing Site element | DADS reference | Action in v0.1 |
|---|---|---|
| Site header and two navigation links | Header container / horizontal menu / link text | Keep the compact two-link information architecture. Use destination-page labels, `aria-current`, DADS blue current indicator, underlined link treatment, and the Yellow-300 plus black focus indicator. |
| Header `検索` link | Horizontal menu plus Site URL-state contract | Preserve the current recognized `/search` or `/results` query. On detail/about pages, use a session-scoped last valid canonical search query. Never retain `page`, scroll position, record identity, unknown parameters, or invalid values. |
| Search form sections | Form controls / typography / spacing | Keep the existing numbered one-column order. Remove the large dashboard-like panel treatment and use section dividers and a restrained 8 px spacing rhythm. |
| University autocomplete | Combobox / input text | Keep the exact-match-only search semantics and current ARIA combobox structure. Apply DADS input, option, focus, and error presentation. No dependency is added because the DADS v2.18.0 HTML implementation is still marked as planned. |
| Multi-select filters | Checkbox | Keep native checkbox inputs and full clickable labels. Use DADS small-size anatomy with a 24 px control and at least 44 px row target. |
| Single-select filters | Radio | Keep native radio semantics and explicit `指定なし`. Use DADS small-size anatomy with a 24 px control and at least 44 px row target. |
| GPA text input | Input text | Keep raw draft and validation behavior. Apply the DADS border, 8 px radius, error color, hover, and focus treatment. |
| Prefecture expansion | Disclosure | Keep native `<details>/<summary>`. Add the DADS disclosure icon and focus/expanded treatment; the stable label remains content-specific. |
| Primary and secondary actions | Button | Use DADS solid-fill for submit and outline/text treatment for reset actions, with minimum target size and disabled semantics preserved. |
| Normal and floating live counts | Notification/status presentation | Keep one `aria-live` source only. Use a blue information accent, restrained border/background, and no dashboard styling. The floating copy remains visual-only. |
| Results list | Resource list | Keep each admission as an independent item and link only its title. Use separators instead of card shadows, DADS link styling, compact supporting text, and existing factual badges. |
| Pagination | Page navigation / button | Use visible previous/next text controls and a position counter. Hide a nonexistent direction instead of showing a disabled button. Query and ordering semantics remain unchanged. |
| Detail fields | Description list | Keep the established section order and all values. Use restrained name/value rows and DADS typography, spacing, and separators. |
| Warnings and previous-year messages | Semantic notification colors | Preserve all wording and conditions. Use non-color text plus border/background cues and DADS semantic color tokens. |
| About page | Typography / link text / disclosure | Preserve content. Apply the same heading, paragraph, disclosure, and link system. |

## Foundation decisions

### Color

- Primary/key color: DADS Blue-900 `#0017c1`.
- Link color: DADS Blue-1000 `#00118f`; hover Blue-900; active Orange-800.
- Body text: Neutral solid gray 800 `#333333`; stronger text gray 900
  `#1a1a1a`.
- Dividers: Neutral solid gray 420 `#949494` where a strong boundary is
  required, and lighter neutral gray for repeated rows.
- Focus: DADS Yellow-300 `#ffd43d` plus a 4 px black outline and 2 px yellow
  outer ring. This pairing is not customized.
- Error: DADS semantic error 1 (Red-800 `#ec0000`).

### Typography and spacing

- Use the DADS Japanese sans-serif stack beginning with `Noto Sans JP`, then
  platform sans-serif fallbacks. No external web-font request is introduced.
- Preserve readable Japanese body line-height (approximately 1.7) and a
  restrained heading hierarchy.
- Primary inputs, choices, buttons, result titles, and body copy remain 16 CSS
  px or larger. Compact supporting metadata (help text, badges, source labels,
  and the mobile header) may use 12–15 px to preserve the established
  information density; it is not used for the main task text or control label.
- Use an 8 px-based spacing rhythm. The search/results main column remains a
  single compact column of approximately 48 rem.

### Interaction and accessibility

- Links remain visually distinguishable by both color and underline except
  where the horizontal menu's current indicator is the explicit component
  convention.
- All interactive controls have visible keyboard focus using the fixed DADS
  Yellow-300 and black double structure.
- Checkbox and radio labels include the control and keep a practical 44 px
  target row without changing values or ordering.
- The existing live result output remains the only `aria-live` region; the
  floating count stays `aria-hidden`.
- Native semantic elements (`fieldset`, `legend`, `details`, `summary`, `dl`,
  `nav`) remain the base implementation.
- Motion stays minimal and is disabled for users who request reduced motion.

## Canonical header search-state contract

The URL query remains the source of truth for `/search` and `/results`.
`sessionStorage` is only a session-scoped bridge for pages without a search
query, under the key `early-admissions:last-search-query`.

Only values accepted by the existing URL parser are serialized. The stored
query is generated from the parsed `SearchRequest` with `page` forced to 1, so
page number, scroll position, detail identity, draft-only invalid university or
GPA text, unsupported parameters, and unsupported values cannot be persisted.

The header `検索` destination is selected in this order:

1. `/search`: the current recognized form request;
2. `/results`: the current recognized result request;
3. `/admissions/...` and `/about/data`: the stored last valid request;
4. no stored request: `/search`.

A valid form change and a rendered results request update the session bridge.
An invalid in-progress form does not overwrite the last valid stored request.
The header link is ordinary forward navigation and remains independent of the
existing browser-back scroll restoration contract.

## Deliberate non-goals

- No canonical, release, unified, SQLite, or Site-data facts are changed.
- No search parameter, matching rule, classification, or result order changes.
- No React component package, CSS framework, web-font package, or DADS runtime
  dependency is added.
- The DADS card pattern is intentionally not used for every result: Resource
  List is a better match for a dense list of repeated admissions records.
- Hamburger navigation is intentionally not adopted. Two short, stable
  destination links fit without overflow at the supported 320 px minimum.
- The floating live count remains a custom status element because DADS has no
  exact component for this behavior; it uses DADS tokens and keeps the normal
  live output as its accessibility source of truth.
- This mapping does not claim formal DADS or WCAG certification; it records a
  source-referenced migration and its testable implementation choices.
