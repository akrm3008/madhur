# Output Formatting Rules

## Box-Drawing Diagrams

When creating or editing ASCII box-drawing diagrams (using characters like ─ │ ┌ ┐ └ ┘ ├ ┤ ╔ ═ ╗ etc.) in markdown files:

### Layout rules

1. Keep diagrams **narrow** (under 120 characters wide) — wider diagrams drift more
2. **Do not wrap** diagrams in a large outer border box — this doubles alignment constraints and almost always breaks
3. Prefer simple layouts — side-by-side boxes connected with arrows, not nested boxes inside outer borders

### Arrow characters

**Use only narrow-width (EAW=N) arrow characters.** Many Unicode arrows have "Ambiguous" East Asian Width and render as 2 cells in VS Code, Cursor, and CJK terminals, silently breaking vertical alignment. Safe arrows:
- Left: `◄` (U+25C4) or `◂` (U+25C2) — NOT `◀` (U+25C0) or `←` (U+2190)
- Right: `►` (U+25BA) or `▸` (U+25B8) — NOT `▶` (U+25B6) or `→` (U+2192)
- Down: `▾` (U+25BE) — NOT `▼` (U+25BC) or `↓` (U+2193)
- Up: `▴` (U+25B4) — NOT `▲` (U+25B2) or `↑` (U+2191)
- Long left: `⟵` (U+27F5) — NOT `←` (U+2190)
- Long right: `⟶` (U+27F6) — NOT `→` (U+2192)

### Box width consistency (the #1 source of errors)

**Every line of a box must have the exact same character count.** The validator checks that each box-drawing character connects to another box-drawing character on the adjacent line in the expected direction. If one line is even 1 character wider or narrower, the closing `│` or `┐` shifts and the validator reports errors on every surrounding line.

**How to count:** For a box whose longest content is N visible characters:
```
inner_width = N + left_pad + right_pad   (typically 1 space each side)
top/bottom  = ┌ + (inner_width × ─) + ┐  →  total = inner_width + 2
content     = │ + (inner_width chars)  + │  →  total = inner_width + 2
```

**Example** — a box for `endpoint_values` (16 chars), 1-space padding each side:
```
┌──────────────────┐   ← 20 chars total (18 dashes + 2 corners)
│ endpoint_values  │   ← 20 chars total (│ + space + 16 chars + space + │)
└──────────────────┘   ← 20 chars total (18 dashes + 2 corners)
```

**Common mistake:** Trailing spaces. `│ endpoint_values  │` with an extra space before `│` makes the content line 21 chars while the borders stay at 20. This is invisible to the eye but breaks the validator on every adjacent line.

### Side-by-side boxes

When placing boxes next to each other horizontally, each box must be independently width-consistent. The gap between boxes is just spaces — it does not need to be a fixed width, but must be consistent across all rows of that diagram section.

### Connectors and branches

When a connector character (`├`, `┼`, `┬`, `┴`) replaces part of a box border, it must land at the **exact same column** as the `│` it replaces. If you change a box's width, you must adjust all connector positions downstream.

**Branching to distant targets:** To connect one box to two boxes that aren't adjacent, use a horizontal branch:
```
┌──────┐
│ host │
└──┬───┘
   │
   ├───────────────┐
   │               │
   ▾               ▾
┌──────────┐  ┌────────────┐
│ endpoints│  │ endpoint_  │
│          │  │ leads      │
└──────────┘  └────────────┘
```

### After every edit

1. **Run the ascii-diagram-validator** to check alignment:
   ```
   uv run scripts/check_ascii_alignment.py <file>
   ```
2. If the validator reports errors, fix them before considering the edit complete
3. If fixing one box shifts a closing `│`, check downstream connectors and branches too
