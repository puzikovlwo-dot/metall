# Pre-publish checklist

Run these in order before every `git push` to `main`.

## 1. Static checks

```bash
# Import-time error check (catches missing imports, typos, etc.)
python -c "import app"

# Should print: 2000 30 178 (or similar — exact row counts may differ
# if data_prep.py was tweaked). For the canonical generator: 2000, 30, 178.
python -c "import pandas as pd; print(len(pd.read_csv('sales.csv')), len(pd.read_csv('plans.csv')), len(pd.read_csv('clients.csv')))"
```

Expected: `2000 30 178` (or whatever current canonical counts are — verify with `wc -l *.csv` once).

## 2. Smoke test (optional but recommended)

```bash
python .claude/skills/metall-dashboard/scripts/smoke_test.py
```

Boots the app on an unused port, hits each registered route, then kills the process. Exits 0 on success, non-zero on any failure. Catches callback signature errors that static import misses.

## 3. Visual check

```bash
python app.py
# open http://127.0.0.1:8050 in browser
# verify:
#  - default role (Директор) renders all 6 KPI cards without "—"
#  - switch role to "Менеджер" → manager dropdown appears, KPIs drop to one manager
#  - change date range → all charts and KPIs update
#  - open clients modal → table populates
#  - click "Экспорт CSV" → file downloads
```

## 4. README sync check

If the change touched any of the following, update `README.md`:

- [ ] New dependency in `pip install ...` line
- [ ] New KPI card, chart, or table column
- [ ] New filter
- [ ] New status / category / client type
- [ ] File renamed or added (update `Структура проекта` tree)
- [ ] New run command (e.g. CLI flag)

If only data files changed, no README update is needed.

## 5. Encoding audit

```bash
git diff --stat
# look for .csv files modified
# any new .to_csv() call must use encoding='utf-8-sig'
```

Quick grep:

```bash
grep -rn "to_csv" --include="*.py" .
```

Every hit must pass `utf-8-sig`.

## 6. Git hygiene

```bash
git status                    # only intended files staged
git log --oneline -5          # recent commit messages follow Conventional Commits
```

Commit message prefixes used in this project:
- `feat:` — new user-facing feature
- `fix:` — bug fix
- `refactor:` — internal change, no behavior shift
- `docs:` — README / СТРУКТУРА / comments
- `chore:` — data regen, .gitignore, tooling
- `style:` — formatting only

## 7. Push

```bash
git push origin main
```

If push is rejected (e.g. someone else pushed first): `git pull --rebase origin main`, re-run step 1 (smoke test), then push.

## When the change is breaking (e.g. data schema)

1. Update `СТРУКТУРА_ДАННЫХ.md` first — it is the schema source of truth.
2. Then update `data_prep.py` and `app.py`.
3. Then update `README.md`.
4. Re-run steps 1–3 above.
5. Commit message must include `BREAKING CHANGE:` in the footer.
