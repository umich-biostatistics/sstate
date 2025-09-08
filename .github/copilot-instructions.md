# AI Coding Agent Instructions for `sstate`

These guidelines equip an AI agent to work effectively in this repository. Focus on reflecting actual patterns; avoid inventing structure or frameworks.

## 1. Project Purpose & Scope
`sstate` is a single-file Python CLI tool that queries a Slurm cluster (`scontrol show nodes --oneliner`) and presents a color-coded summary of node CPU and memory utilization plus aggregate totals. It replaces an older Perl utility; simplicity and zero-runtime-dependency deployment (via PyInstaller) are deliberate goals.

## 2. Key Files
- `sstate.py` – Entire application logic (arg parsing, Slurm call, parsing, formatting, output). Keep it lean; adding external modules should be justified.
- `build.py` – PyInstaller build orchestration; wraps the CLI-friendly build with error surfacing.
- `Makefile` – Developer workflow entry points (virtualenv management, build, install, clean, test).
- `sstate.spec` – Generated/checked-in PyInstaller spec; mirrors flags in `build.py` (keep them synchronized if you change one).
- `requirements.txt` – Runtime (tabulate, colorama) + build (pyinstaller) dependencies.

## 3. Runtime Behavior
- External command: executes `scontrol` via `subprocess.check_output("$(/usr/bin/which scontrol) show nodes --oneliner", shell=True)`. Assumes Slurm client tools installed and in PATH. Do not silently change this without justification; if enhancing, gate fallback logic behind an opt-in flag.
- Output: Two tables (per-node + cluster totals) plus usage legend. Colors use `colorama.init(autoreset=True)`; avoid printing raw ANSI before init.
- Memory units: Input values assumed in MB (Slurm RealMemory). Converted with custom `human_readable` (1024 base, suffix Mi/Gi/Ti...). Preserve this function if refactoring.

## 4. Parsing Strategy
- Raw `scontrol` output is split lines; each line is tokenized using `re.split(r"([A-Z]\w+=)")` and reconstructed into `Key=Value` segments.
- `reformat_scontrol_output` builds a list-of-lists (per node list of `Key=Value` strings). Subsequent passes re-scan each list; performance is acceptable for typical cluster sizes. If optimizing, maintain identical output semantics.
- `filter_partition_node_data` matches `Partitions=` field; special-case `debug` partition logic is intentionally preserved.
- `parse_node_data` accumulates totals while building formatted rows; modifies running totals inline. If extracting model objects, ensure numeric accumulation order stays deterministic.

## 5. Formatting & Color Rules
- CPU & Memory usage columns show percent + bar (0–10 chars of `█`). Color thresholds: 0 (none), 1–25% Yellow, 25–50% Blue, 50–75% Cyan, 75–100% Bright Green.
- Node state coloring precedence: any of `down|drain|fail|error` => Bright Red; then allocated/alloc => Green; mixed => Yellow; idle => default; else uncolored.
- Legend text must stay aligned with logic if thresholds change.

## 6. Build & Distribution Workflow
Preferred paths (documented in README):
- Virtualenv: `make venv` (auto when building if `USE_VENV=1`).
- Build: `make build` (calls `python build.py`). Produces `./dist/sstate`.
- Clean: `make clean` (PyInstaller artifacts) / `make clean-all` (also venv).
- Install: `make install` copies binary to `/usr/local/bin/sstate` (needs sudo).
- Direct script run (development): `pip install -r requirements.txt && python sstate.py`.
Keep consistency between `build.py` flags and `sstate.spec` (if altering `--add-data`, name, or `upx` usage).

## 7. Dependency & Version Notes
- Python >= 3.7 target (avoid 3.12-only syntax). Use only the listed third-party libs unless a compelling, minimal addition.
- `pyinstaller` is a build-time dep; do not require it at runtime inside `sstate.py`.

## 8. Extending the Tool (Guided Boundaries)
Acceptable incremental enhancements:
- Optional flags (e.g., JSON output `--json`, alternative sort order) – must not break default human table output.
- Error handling: Wrap the `scontrol` call to emit a clear message if Slurm isn't available (non-zero exit) without a traceback.
- Performance: Avoid premature micro-optimizations; clarity over speed unless cluster sizes cause measurable lag.
Avoid:
- Splitting into many modules unless complexity justifies; single-file simplicity is intentional.
- Adding heavy frameworks (Click, Rich) unless explicitly requested.

## 9. Testing & Validation Suggestions
(No formal test suite yet.) For new features, add a lightweight script or doc snippet showing parsing of a captured sample `scontrol` line. If creating tests, prefer fixtures of raw `scontrol` output and assert table row field extraction + aggregate stats.

## 10. Style & Conventions
- Keep functions pure where feasible (formatting separated from aggregation is acceptable but not enforced currently).
- Avoid global mutable state; accumulate within `parse_node_data` scope.
- Follow existing naming (snake_case) and simple docstring patterns.

## 11. Common Pitfalls
- Passing malformed partition names: current code silently yields empty tables if filter removes all nodes; if changing, avoid breaking existing behavior unless adding an explicit message.
- Memory or CPU values that fail `int()` or `float()` parsing default to 0 (defensive). Preserve this guard logic.
- Reordering columns: Downstream users may parse the grid output; coordinate before changing header order or labels.

## 12. Safe Refactor Checklist
When editing `sstate.py`:
- Run: `python sstate.py --help` (still works?)
- Mock/record `scontrol` output for offline validation if you cannot access Slurm.
- Confirm color legend matches thresholds.
- Rebuild binary: `make build` and smoke test `./dist/sstate -p <partition>`.

---
Questions or clarifications needed? Suggest them, and they can be added here to refine guidance.
