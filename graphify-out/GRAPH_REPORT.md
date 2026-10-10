# Graph Report - TIMSS 2027  (2026-10-02)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 222 nodes · 409 edges · 16 communities (10 shown, 6 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 41 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 7
- Community 8
- Community 10
- Community 11
- Community 13
- Community 14

## God Nodes (most connected - your core abstractions)
1. `SVG` - 33 edges
2. `fmt()` - 12 edges
3. `showItem()` - 11 edges
4. `RENDER` - 10 edges
5. `verify_item()` - 9 edges
6. `finish()` - 9 edges
7. `reviewScreen()` - 9 edges
8. `_axes_frame()` - 9 edges
9. `bar_chart()` - 9 edges
10. `histogram()` - 9 edges

## Surprising Connections (you probably didn't know these)
- `main()` --calls--> `render()`  [EXTRACTED]
  scripts/build_bank.py → scripts/figures.py
- `render_figures()` --calls--> `render()`  [EXTRACTED]
  scripts/build_bank.py → scripts/figures.py

## Import Cycles
- None detected.

## Communities (16 total, 6 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.08
Nodes (13): main(), md_table(), safe(), write(), brand_info(), encrypt_form(), inline_katex_css(), js_safe() (+5 more)

### Community 1 - "Community 1"
Cohesion: 0.10
Nodes (22): card_id(), coverage_report(), equal(), js_to_py(), Linter, load_yaml(), Log, main() (+14 more)

### Community 2 - "Community 2"
Cohesion: 0.15
Nodes (25): askCode(), captureResponse(), checkPractice(), cycleFont(), demoResponse(), exitSession(), finish(), navbar() (+17 more)

### Community 3 - "Community 3"
Cohesion: 0.19
Nodes (12): _all_int(), _axes_frame(), bar_chart(), coord(), Y(), fmt(), histogram(), line_chart() (+4 more)

### Community 4 - "Community 4"
Cohesion: 0.17
Nodes (6): cardNode(), RENDER, onDrop(), render(), reveal(), sync()

### Community 5 - "Community 5"
Cohesion: 0.17
Nodes (7): cone(), cylinder(), esc(), fraction_bar(), sphere(), spinner(), SVG

### Community 6 - "Community 6"
Cohesion: 0.12
Nodes (5): bag(), cuboid(), grid_model(), pyramid(), tri_prism()

### Community 7 - "Community 7"
Cohesion: 0.31
Nodes (4): build(), error(), fmt(), render()

### Community 8 - "Community 8"
Cohesion: 0.33
Nodes (5): geo(), collect(), extend(), P(), polygon_fig()

### Community 10 - "Community 10"
Cohesion: 0.33
Nodes (4): _icon(), _legend(), pictograph(), _text_w()

## Knowledge Gaps
- **6 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SVG` connect `Community 5` to `Community 3`, `Community 6`, `Community 8`, `Community 10`, `Community 11`, `Community 13`, `Community 14`?**
  _High betweenness centrality (0.074) - this node is a cross-community bridge._
- **Why does `geo()` connect `Community 8` to `Community 5`, `Community 6`?**
  _High betweenness centrality (0.025) - this node is a cross-community bridge._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.08258258258258258 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.09682539682539683 - nodes in this community are weakly interconnected._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.14962121212121213 - nodes in this community are weakly interconnected._
- **Should `Community 6` be split into smaller, more focused modules?**
  _Cohesion score 0.11764705882352941 - nodes in this community are weakly interconnected._