# Data schema reference

**Source of truth:** `СТРУКТУРА_ДАННЫХ.md` in repo root. This file is a quick-reference card for the agent — load only when the task touches data.

## `sales.csv` — 2000 rows

| Column | Type | Notes |
|---|---|---|
| `Дата` | date | `pd.to_datetime` at load. Range: 2026-01-01 .. 2026-06-30. |
| `Номер_договора` | text | Format `Д-2026-NNNNN`. Unique. |
| `ID_клиента` | int | FK → `clients.ID_клиента`. |
| `Название_клиента` | text | Denormalized into sales for convenience. |
| `Тип_клиента` | enum | `Опт` / `Розница`. Split 35/65. |
| `ID_менеджера` | int | 1..5. |
| `ФИО_менеджера` | text | Denormalized. 5 fixed names. |
| `Категория` | enum | `Трубы` / `Лист` / `Арматура` / `Метизы`. |
| `Количество` | int | Units sold. |
| `Цена_за_ед.` | float | BYN. |
| `Сумма` | float | `Количество * Цена_за_ед.`. **Use this, never recompute.** |
| `Статус` | enum | `Оплачено` (~65%) / `В работе` (~20%) / `Отменено` (~10%) / `Отозвано` (~5%). Probability matrix depends on `(Тип_клиента, Категория)`. |

## `plans.csv` — 30 rows

| Column | Type | Notes |
|---|---|---|
| `ID_менеджера` | int | 1..5. |
| `Месяц` | date | First day of month. 6 months. |
| `Плановая_сумма` | float | BYN. Base ±5% random jitter. |

## `clients.csv` — ~178 rows

| Column | Type | Notes |
|---|---|---|
| `ID_клиента` | int | PK. |
| `Дата_первой_сделки` | date | |
| `Название_клиента` | text | |
| `Тип_клиента` | enum | `Опт` / `Розница`. |
| `ID_менеджера_первой_сделки` | int | FK → sales `ID_менеджера`. |
| `Менеджер_первой_сделки` | text | Denormalized. |
| `Статус_клиента` | enum | `Новый` (1 deal ever) / `Старый` (2+). Split ~14/86. |
| `Всего_сделок` | int | |
| `Общая_сумма` | float | |
| `Оплачено` | int | Count of `Оплачено` deals. |
| `Отменено` | int | Count of `Отменено` deals. |

## Relationships

```
sales.ID_клиента            ── clients.ID_клиента
sales.ID_менеджера          ── plans.ID_менеджера  (per-month)
sales.ID_менеджера          ── clients.ID_менеджера_первой_сделки
```

## Special distributions (do not "fix" these)

- **Pareto**: 20% of clients drive 80% of sales. Hard-coded in `data_prep.py`.
- **Seasonality**: peaks in March and June (quarter/semi-annual close), trough in January and May.
- **Manager specialization**: each manager has a fixed `(client_type_bias, category_bias)`. Don't change in mid-cycle.
- **Status probability matrix**: depends on `(Тип_клиента, Категория)`. E.g. опт + трубы → 82% Оплачено; розница + мети зы → 55%.

## Loaded once in `app.py:17–33`

```python
for f in ['sales.csv', 'plans.csv', 'clients.csv']:
    if not os.path.exists(f):
        # auto-generate via data_prep on first run
        ...
df_sales['Дата'] = pd.to_datetime(df_sales['Дата'])
df_plans['Месяц'] = pd.to_datetime(df_plans['Месяц'])
df_clients['Дата_первой_сделки'] = pd.to_datetime(df_clients['Дата_первой_сделки'])
```

Never read CSVs from callbacks — use the already-loaded `df_sales`, `df_plans`, `df_clients`.
