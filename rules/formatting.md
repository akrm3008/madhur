# Output Formatting Rules

## Box-Drawing Diagrams

When creating or editing ASCII box-drawing diagrams (using characters like ─ │ ┌ ┐ └ ┘ ├ ┤ ╔ ═ ╗ etc.) in markdown files:

1. Keep diagrams **narrow** (under 120 characters wide) — wider diagrams drift more
2. **Do not wrap** diagrams in a large outer border box — this doubles alignment constraints and almost always breaks
3. **Use only narrow-width (EAW=N) arrow characters.** Many Unicode arrows have "Ambiguous" East Asian Width and render as 2 cells in VS Code, Cursor, and CJK terminals, silently breaking vertical alignment. Safe arrows:
   - Left: `◄` (U+25C4) or `◂` (U+25C2) — NOT `◀` (U+25C0) or `←` (U+2190)
   - Right: `►` (U+25BA) or `▸` (U+25B8) — NOT `▶` (U+25B6) or `→` (U+2192)
   - Down: `▾` (U+25BE) — NOT `▼` (U+25BC) or `↓` (U+2193)
   - Up: `▴` (U+25B4) — NOT `▲` (U+25B2) or `↑` (U+2191)
   - Long left: `⟵` (U+27F5) — NOT `←` (U+2190)
   - Long right: `⟶` (U+27F6) — NOT `→` (U+2192)
4. After writing or editing any file containing box-drawing diagrams, **run the ascii-diagram-validator** to check alignment:
   ```
   uv run scripts/check_ascii_alignment.py <file>
   ```
5. If the validator reports errors, fix them before considering the edit complete
