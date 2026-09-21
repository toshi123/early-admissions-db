# Third-party notices

## Digital Agency Design System HTML code snippets

The Site UI includes adaptations of visual and accessibility patterns from the
Digital Agency Design System HTML code snippets:

- source: <https://github.com/digital-go-jp/design-system-example-components-html>
- referenced commit: `af8b6656c8d864a22ef444d088e5568f3416f6aa`

The source project is provided under the MIT License:

> MIT License
>
> Copyright (c) 2025 デジタル庁
>
> Permission is hereby granted, free of charge, to any person obtaining a copy
> of this software and associated documentation files (the "Software"), to deal
> in the Software without restriction, including without limitation the rights
> to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
> copies of the Software, and to permit persons to whom the Software is
> furnished to do so, subject to the following conditions:
>
> The above copyright notice and this permission notice shall be included in all
> copies or substantial portions of the Software.
>
> THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
> IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
> FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
> AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
> LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
> OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
> SOFTWARE.

The Digital Agency does not endorse this project. The repository incorporates
only the patterns documented in the UI mapping; it does not redistribute the
complete upstream snippet package.

## ExcelJS browser export

The candidate-list Excel export dynamically loads `@protobi/exceljs`
`4.4.0-protobi.10`, the maintained Protobi fork of ExcelJS.

- Fork source: <https://github.com/protobi/exceljs>
- Original source: <https://github.com/exceljs/exceljs>
- npm package: <https://www.npmjs.com/package/@protobi/exceljs>
- License text below is from the pinned package's `LICENSE` file.
- The lockfile records the exact package and transitive dependency versions.
- This document is copied to `/third-party-notices.txt` during Site-data sync
  and included in the production distribution. That generated copy is ignored.

> The MIT License (MIT)
>
> Copyright (c) 2014-2019 Guyon Roche
>
> Permission is hereby granted, free of charge, to any person obtaining a copy
> of this software and associated documentation files (the "Software"), to deal
> in the Software without restriction, including without limitation the rights
> to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
> copies of the Software, and to permit persons to whom the Software is
> furnished to do so, subject to the following conditions:
>
> The above copyright notice and this permission notice shall be included in all
> copies or substantial portions of the Software.
>
> THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
> IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
> FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
> AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
> LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
> OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
> SOFTWARE.

### Security review (2026-09-21)

The fork's npm metadata reports an update on 2026-05-07. Its real OOXML writer
supports frozen panes, autofilter, text cells, hyperlinks and wrapping without
a second application-level export dependency. It adds 145 installed packages,
including transitive dependencies; this cost is not hidden.

`npm audit` reports **2 moderate entries, 0 high, 0 critical**: `uuid` plus the
parent `@protobi/exceljs`. Both trace to one advisory,
<https://github.com/advisories/GHSA-w5hq-g745-h8pq>, for buffer bounds checks in
uuid v3/v5/v6 with caller-provided buffers (affected versions <11.1.1).
The package uses uuid v4; this feature only writes a workbook, without pivot
tables/conditional formatting or caller-provided uuid buffers, and never reads
untrusted workbooks. This is a reachability assessment, not a claim that the
dependency is patched or vulnerability-free. The prebuilt browser bundle
embeds its dependencies: a lockfile-only uuid override would not fix it.
Keep the finding visible and recheck the upstream browser build before a
future release. No `audit fix --force` or validation bypass is used.
