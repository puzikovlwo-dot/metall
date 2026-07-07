---
name: metall-dashboard
description: This skill should be used when the user works on the METALL (Аксвил) sales dashboard project — a Python Dash + Plotly + Pandas + Bootstrap app. Apply when the user asks to "run the dashboard", "start the server", "regenerate data", "add a KPI", "add a filter", "add a chart", "fix a callback", "update README", "publish to GitHub", "prepare a release", "check for errors", "refactor app.py", or mentions the Аксвил/METALL project, продажи, менеджеры, KPI-карточки, графики, фильтры, роли.
version: 0.1.0
---

# METALL — Дашборд продаж «Аксвил»

## What this project is

A single-page **Dash** dashboard for the sales department of «Аксвил» (metal products). Russian-language UI, B2B-style. Three CSVs as the data source, one Python file for the entire app.

## Tech stack (locked in)

- Python 3.10+
- `dash`, `dash-bootstrap-components`, `plotly`, `pandas`, `numpy`
- Dash runs on default port `8050` (http://127.0.0.1:8050)
- CSV I/O with `encoding='utf-8-sig'` (Excel-compatible Russian)

## Project structure (current)

```
metall/
├── data_prep.py        # Test data generator (np.random.seed(42))
├── app.py              # All Dash app code: load, filters, KPIs, callbacks, UI
├── sales.csv           # 2000 deals, Jan–Jun 2026
├── plans.csv           # 30 rows (5 managers × 6 months)
├── clients.csv         # ~178 clients
├── README.md
├── СТРУКТУРА_ДАННЫХ.md  # Authoritative data schema
└── .claude/skills/metall-dashboard/   # this skill
```

## Quick commands

| Action | Command |
|---|---|
| Regenerate data | `python data_prep.py` |
| Run dashboard | `python app.py` |
| Lint-style check | `python -c "import app"` (catches import/load errors) |
| Smoke-test data | `python -c "import pandas as pd; print(pd.read_csv('sales.csv').shape)"` |
| Publish to GitHub | `git add -A && git commit -m "..." && git push` |

## Conventions to preserve

1. **Encoding** — always `utf-8-sig` when writing CSVs; reads use plain `pd.read_csv`.
2. **Date columns** — `pd.to_datetime(...)` applied at load time in `app.py` lines 28–33.
3. **Role-based isolation** — `filter_data()` is the single source of truth for row-level filtering. New filters must extend it, not bypass it.
4. **Plan proration** — `prorated_plan()` already implements month-boundary-aware proration. Reuse it; do not duplicate the logic.
5. **Color palette** — `C` dict in `app.py` (lines 49–60) is the only place to add a new color. CSS-in-Python, not external stylesheets.
6. **Russian labels** — user-facing strings stay in Russian. Field names in DataFrames use Russian column names (`Дата`, `Сумма`, `Категория`); do not rename them.
7. **Statuses** — four deal statuses (`Оплачено`, `В работе`, `Отменено`, `Отозвано`); two client types (`Опт`, `Розница`); four categories (`Трубы`, `Лист`, `Арматура`, `Метизы`). Treat as enums.
8. **No external state** — no database, no auth, no env vars. Everything in CSV + `app.py`. Keep it that way unless asked.

## Common tasks — workflow

### Run / restart the server

1. Kill any process on port 8050: `lsof -ti:8050 | xargs kill -9` (POSIX) or `netstat -ano | findstr :8050` + `taskkill /PID <pid> /F` (Windows).
2. Start: `python app.py`.
3. Open http://127.0.0.1:8050.

### Change a KPI card

1. Find the KPI block in `app.py` (look for `dbc.Card` inside the `kpi_row`).
2. Keep the four-line structure: label, value, delta, helper.
3. Recompute against the already-filtered `dff` — never re-filter.

### Add a filter

1. Add the `dcc.Dropdown` / `dcc.DatePickerRange` in the filter row.
2. Add the input to the existing `@callback` signature.
3. Extend `filter_data()` with a new `if` clause (do not change the existing ones).
4. Verify the new output appears in the URL/State propagation (filters feed every KPI, chart, and table callback).

### Regenerate data

Run `python data_prep.py`. Output is deterministic (seed=42), so re-running produces identical files. To vary: change `np.random.seed(42)` in `data_prep.py:7`.

### Update README

The README is the project's public face. Keep these sections in sync when touching code:
- **Функциональность** — features list
- **Установка и запуск** — pip command and run command
- **Структура проекта** — file tree
- **Данные** — column lists with descriptions

For the canonical data schema, defer to `СТРУКТУРА_ДАННЫХ.md` and only link to it; do not duplicate.

### Prepare a release / publish

1. Verify `git status` is clean except for intended changes.
2. Run `python -c "import app"` to catch import-time errors.
3. Update `README.md` if user-facing behavior changed.
4. Commit with a Conventional Commits-style message: `feat:`, `fix:`, `chore:`, `docs:`.
5. Push: `git push origin main`.

## Error patterns to watch for

- **`KeyError: 'Дата'`** — a new code path is reading a column without going through `pd.to_datetime`. Always load via the top-of-file block in `app.py`.
- **Callback output count mismatch** — Dash requires every `@callback` to return the exact number of declared `Output`s. After adding a KPI, update the tuple.
- **`utf-8-sig` dropped on manual `to_csv`** — only the loaders in `app.py` and `data_prep.py` should write CSVs.
- **Empty dataframes in callbacks** — show `—` / `Нет данных`; do not return `None` to a `dcc.Graph`.

## Additional resources

### Reference files (load on demand)

- **`references/data-schema.md`** — canonical field-by-field data schema. Read before touching data files.
- **`references/callback-map.md`** — map of every `@callback` in `app.py`: inputs, outputs, side effects. Read before adding callbacks.
- **`references/release-checklist.md`** — step-by-step pre-publish checklist.

### Scripts (run directly, no need to read)

- **`scripts/smoke_test.py`** — boots the app headlessly and asserts that all data loads, no callback signature errors, every page route responds. Run before any push.
- **`scripts/regen_data.sh`** — one-shot `python data_prep.py` wrapper with a confirmation prompt.
