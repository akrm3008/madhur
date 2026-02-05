# Output Formatting Rules

## Tables

Never use markdown table syntax (pipe-based tables) in conversational output. The terminal renderer frequently breaks markdown tables, causing misaligned columns, garbled output, or only the last row displaying.

Instead, always present tabular data using one of these approaches:

1. **Code-fenced tables** (preferred for structured data):

```
Name          Status      Count
─────────────────────────────────
boundaries    active      350
reviews       complete    12
memberships   active      15237
```

2. **Bulleted lists** (preferred for fewer than 5 items or when columns aren't needed):

- **boundaries**: 350 active
- **reviews**: 12 complete
- **memberships**: 15,237 active

3. **Indented key-value pairs** (preferred for single-record detail):

```
Table:   boundary_reviews
Rows:    12
Columns: id, tld_id, label, reviewed_by, reviewed_at
```

This rule applies to conversational output only. Markdown tables are fine when writing to files (e.g., README.md, documentation).

## Box-Drawing Diagrams

When creating or editing ASCII box-drawing diagrams (using characters like ─ │ ┌ ┐ └ ┘ ├ ┤ ╔ ═ ╗ etc.) in markdown files:

1. Keep diagrams **narrow** (under 120 characters wide) — wider diagrams drift more
2. **Do not wrap** diagrams in a large outer border box — this doubles alignment constraints and almost always breaks
3. After writing or editing any file containing box-drawing diagrams, **run the ascii-diagram-validator** skill to check alignment:
   ```
   uv run ${CLAUDE_PLUGIN_ROOT}/skills/ascii-diagram-validator/scripts/check_ascii_alignment.py <file>
   ```
4. If the validator reports errors, fix them before considering the edit complete
5. Prefer simple layouts — side-by-side boxes connected with arrows, not nested boxes inside outer borders
