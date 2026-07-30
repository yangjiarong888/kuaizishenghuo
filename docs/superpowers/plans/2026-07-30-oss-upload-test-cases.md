# OSS Upload Test Cases Workbook Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and visually verify a detailed Excel workbook containing executable OSS upload-chain test cases, business-entry regression coverage, reusable test data, and execution records.

**Architecture:** Use one auditable JavaScript builder backed by the bundled `@oai/artifact-tool`. Keep source data as explicit arrays, derive workbook statistics with Excel formulas, apply a shared style system to all sheets, export once, and verify the saved workbook through structured inspection plus rendered images.

**Tech Stack:** Bundled Node.js runtime, `@oai/artifact-tool`, Excel `.xlsx`.

## Global Constraints

- Source baseline is `origin/release`; the source document date is 2026-07-27.
- Create exactly five sheets: `用例说明与统计`, `核心测试用例`, `业务入口回归矩阵`, `测试数据清单`, `执行记录`.
- Save the final workbook under `outputs/2026-07-30-oss-upload-test-cases/`.
- Use only loader-provided executables and dependencies; do not install or substitute spreadsheet libraries.
- Core cases must contain non-empty IDs, titles, steps, and expected results.
- Business entries must cover normal image, abnormal image, and OSS failure; video entries must additionally cover MP4 and first-frame generation.
- Summary counts must be formulas or traceable table values.
- Freeze headers, enable filters, wrap text, and verify all sheets visually.

---

## File Structure

- Create: `.tmp/oss-upload-test-cases/build_workbook.mjs`
  - Owns source arrays, workbook construction, formulas, styles, inspection, rendering, and export.
- Create: `outputs/2026-07-30-oss-upload-test-cases/OSS上传链路详细测试用例.xlsx`
  - Final user-facing workbook.
- Create: `.tmp/oss-upload-test-cases/rendered/*.png`
  - Temporary sheet previews used only for visual verification.

### Task 1: Prepare the supported workbook runtime

**Files:**
- Create: `.tmp/oss-upload-test-cases/build_workbook.mjs`

**Interfaces:**
- Consumes: `codex_app.load_workspace_dependencies()` response and the complete spreadsheet API quick-start/style references.
- Produces: an executable module able to import `@oai/artifact-tool` from a junctioned `node_modules`.

- [ ] **Step 1: Load the workspace dependency manifest**

Call `codex_app.load_workspace_dependencies()` and record the exact bundled Node executable and `node_modules` path.

- [ ] **Step 2: Read required spreadsheet references completely**

Read:

```text
<spreadsheets-skill>/style_guidelines.md
<spreadsheets-skill>/artifact_tool_docs/API_QUICK_START.md
```

- [ ] **Step 3: Create the task directory and dependency junction**

Create `.tmp/oss-upload-test-cases/` and a Windows directory junction:

```powershell
New-Item -ItemType Directory -Force '.tmp\oss-upload-test-cases'
New-Item -ItemType Junction -Path '.tmp\oss-upload-test-cases\node_modules' -Target '<loader-provided-node_modules>'
```

- [ ] **Step 4: Add the initial module imports and constants**

Create `.tmp/oss-upload-test-cases/build_workbook.mjs` with:

```js
import fs from "node:fs/promises";
import path from "node:path";
import { Workbook, SpreadsheetFile } from "@oai/artifact-tool";

const rootDir = path.resolve(".");
const outputDir = path.join(rootDir, "outputs", "2026-07-30-oss-upload-test-cases");
const renderDir = path.join(rootDir, ".tmp", "oss-upload-test-cases", "rendered");
const outputPath = path.join(outputDir, "OSS上传链路详细测试用例.xlsx");
const sourceUrl = "https://kuaizilife-my.sharepoint.com/:w:/g/personal/chenxianwei_daoxing888_com/IQBMj6RG6amkSo4yTJRxk0YoAT4Fop-3XimEyrNMaa3MgBM?rtime=B80YEQ7u3kg";
```

- [ ] **Step 5: Run the module to verify imports**

Run:

```powershell
<bundled-node> '.tmp\oss-upload-test-cases\build_workbook.mjs'
```

Expected: exit code `0`; no module-resolution error.

### Task 2: Define detailed and auditable source data

**Files:**
- Modify: `.tmp/oss-upload-test-cases/build_workbook.mjs`

**Interfaces:**
- Produces:
  - `coreCases: TestCase[]`
  - `businessEntries: BusinessEntry[]`
  - `testData: TestDataItem[]`
  - `executionHeaders: string[]`

Use these exact row contracts:

```js
// TestCase:
["用例编号","模块","用例标题","测试类型","优先级","前置条件","测试数据",
 "操作步骤","预期结果","数据库/OSS检查点","自动化建议","执行结果","缺陷编号","备注"]

// BusinessEntry:
["序号","端/模块","业务入口","接口路由（执行前补录）","正常图片","异常图片",
 "OSS失败","MP4/首帧","关联核心用例","优先级","执行结果","备注"]

// TestDataItem:
["数据编号","数据类别","文件/数据说明","关键参数","用于验证","预期处理","准备方式","可复用"]
```

- [ ] **Step 1: Add core image-upload cases**

Add individual cases for:

```text
JPEG/JPG/PNG/GIF/WebP successful upload
CDN accessibility and page display
high-resolution original pixel and MD5 preservation
pic_cover versus mid/small/micro display-path correctness
absence of unexpected x-oss-process resize
50,000,000-pixel lower boundary, exact boundary, and upper boundary
empty file, forged extension, corrupted image
BMP/TIF/SVG/PSD/ICO rejection
5 MB lower boundary, exact boundary, and upper boundary
zero-byte and filename/extension case compatibility
```

Each row must include numbered steps and observable interface/page plus OSS expectations.

- [ ] **Step 2: Add processing and consistency cases**

Add individual cases for:

```text
700/360/240/60 derivative generation and dimensions
city lower-right watermark
business-license tiled watermark
JPEG/WebP watermark re-encoding behavior
two valid files batch success
valid+invalid batch atomic failure
uploaded OSS object cleanup
local temporary-file cleanup
business record not partially written
```

- [ ] **Step 3: Add video, deletion, and failure cases**

Add individual cases for:

```text
MP4 success with type=2
first-frame cover and watermark
20 MB lower boundary, exact boundary, and upper boundary
non-video rejection
ffmpeg unavailable
cover-generation failure
delete by full CDN URL
delete by object path
delete comma-separated multiple files
delete missing/nonexistent object
OSS authentication, network, and timeout failures
OSS disabled local-save regression
```

- [ ] **Step 4: Add business-closure and non-route cases**

Add individual cases for:

```text
product, housing, review, after-sales, recharge-order record submission
front-end and back-office display
IM group-avatar upload
mini-program QR batch generation
failure must not write invalid image paths
```

- [ ] **Step 5: Add all documented business entries**

Add the full list of business scenarios from the source document, grouped by `通用/PC后台`, `用户端`, `骑手端`, `外卖/商家`, `城市媒体`, `App/WAP`, and `非独立HTTP流程`. Set `接口路由（执行前补录）` to `待按现网接口文档补录` because the source document does not expose route text in the readable table.

- [ ] **Step 6: Add reusable boundary data**

Include at least:

```text
valid JPEG/JPG/PNG/GIF/WebP
49,999,999 / 50,000,000 / 50,000,001-pixel images
5 MB - 1 byte / 5 MB / 5 MB + 1 byte images
19,999,999-byte / 20 MB / 20 MB + 1 byte MP4 files
empty file, corrupted image, forged .jpg, BMP/TIF/SVG/PSD/ICO
watermark reference image and batch valid+invalid set
```

### Task 3: Build and format the five-sheet workbook

**Files:**
- Modify: `.tmp/oss-upload-test-cases/build_workbook.mjs`

**Interfaces:**
- Consumes: source arrays from Task 2.
- Produces: populated `Workbook` object with formulas, styles, filters, and freeze panes.

- [ ] **Step 1: Create the workbook and five sheets**

```js
const workbook = new Workbook();
const summarySheet = workbook.worksheets.add("用例说明与统计");
const caseSheet = workbook.worksheets.add("核心测试用例");
const matrixSheet = workbook.worksheets.add("业务入口回归矩阵");
const dataSheet = workbook.worksheets.add("测试数据清单");
const executionSheet = workbook.worksheets.add("执行记录");
```

- [ ] **Step 2: Populate the summary sheet**

Write title, source link, baseline, environment dependencies (`PHP curl`, `GD`, `ffmpeg`, accessible OSS test bucket), P0/P1/P2 definitions, and formula-driven counts using `COUNTIF` against `核心测试用例`.

Required formulas include:

```excel
=COUNTA('核心测试用例'!A:A)-1
=COUNTIF('核心测试用例'!E:E,"P0")
=COUNTIF('核心测试用例'!E:E,"P1")
=COUNTIF('核心测试用例'!E:E,"P2")
```

- [ ] **Step 3: Populate the four tabular sheets**

Write the exact headers and arrays from Task 2. Add two empty execution rows to `执行记录` with:

```text
测试轮次,测试环境,执行人,开始日期,结束日期,用例总数,通过数,失败数,阻塞数,通过率,缺陷链接,测试结论
```

Set `用例总数` to reference the summary total and set `通过率` to:

```excel
=IF(F2=0,0,G2/F2)
```

- [ ] **Step 4: Apply shared styles**

Apply dark blue title/header fills, white bold header text, alternating light row fills, thin borders, vertical top alignment, and wrapped text. Use compact fixed widths for IDs/status columns and capped widths for steps/expectations. Freeze header rows and enable filters on every data table.

- [ ] **Step 5: Add validations and conditional formatting where supported**

Use list values:

```text
执行结果: 未执行,通过,失败,阻塞,不适用
优先级: P0,P1,P2
```

Color execution statuses consistently: green for `通过`, red for `失败`, amber for `阻塞`, gray for `未执行`.

### Task 4: Export, inspect, render, and repair

**Files:**
- Modify: `.tmp/oss-upload-test-cases/build_workbook.mjs`
- Create: `outputs/2026-07-30-oss-upload-test-cases/OSS上传链路详细测试用例.xlsx`
- Create: `.tmp/oss-upload-test-cases/rendered/*.png`

**Interfaces:**
- Consumes: completed `Workbook`.
- Produces: verified workbook and five preview images.

- [ ] **Step 1: Add compact structural inspections**

Inspect:

```text
用例说明与统计!A1:H25
核心测试用例!A1:N12
业务入口回归矩阵!A1:L12
测试数据清单!A1:H15
执行记录!A1:L5
```

Print only compact NDJSON results.

- [ ] **Step 2: Add formula-error scanning**

Use one regex scan for:

```text
#REF!|#DIV/0!|#VALUE!|#NAME?|#N/A
```

Expected: zero matches.

- [ ] **Step 3: Render every sheet**

Render a representative range from each sheet at readable scale and save one PNG per sheet in `.tmp/oss-upload-test-cases/rendered/`.

- [ ] **Step 4: Export the workbook**

```js
await fs.mkdir(outputDir, { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
```

- [ ] **Step 5: Run the builder**

Run:

```powershell
<bundled-node> '.tmp\oss-upload-test-cases\build_workbook.mjs'
```

Expected: exit code `0`, workbook exists, all five sheets inspect successfully, and formula scan returns zero errors.

- [ ] **Step 6: Review all five rendered PNGs**

Open every preview image and verify:

```text
titles and headers are visible
no severe clipping
wrapped steps and expected results remain readable
summary formulas display results
no blank default sheet exists
status colors and table boundaries are legible
```

- [ ] **Step 7: Repair and rerun once if needed**

Patch only the smallest relevant widths, heights, styles, formulas, or ranges in the builder, rerun the full build, and recheck the affected previews.

- [ ] **Step 8: Verify the final artifact**

Confirm:

```powershell
Get-Item 'outputs\2026-07-30-oss-upload-test-cases\OSS上传链路详细测试用例.xlsx'
```

Expected: a non-empty `.xlsx` file with a current modification timestamp.
