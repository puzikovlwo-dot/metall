# Callback map (`app.py`)

**Read this before adding a new callback or changing filter wiring.** Every callback ID and its wiring is listed here so the agent doesn't have to re-grep `app.py`.

## Component IDs (the contract)

| ID | Type | Purpose |
|---|---|---|
| `role-switcher` | radio | Role: `Директор` / `Коммерческий директор` / `Менеджер` |
| `manager-select` | dropdown | Manager ID (visible only when role == `Менеджер`) |
| `manager-select-container` | div | Wrapper around the manager dropdown; hidden when role != `Менеджер` |
| `date-picker` | range | `start_date` + `end_date` |
| `type-filter` | dropdown | `Тип_клиента`: `Все` / `Опт` / `Розница` |
| `category-filter` | dropdown | `Категория`: `Все` / `Трубы` / `Лист` / `Арматура` / `Метизы` |
| `status-filter` | dropdown | `Статус`: `Все` / `Оплачено` / `В работе` / `Отменено` / `Отозвано` |
| `export-btn` | button | Triggers CSV download |
| `download` | dcc.Download | Receives CSV data |
| `btn-clients` | button | Opens clients modal |
| `btn-clients-close` | button | Closes clients modal |
| `clients-modal` | dbc.Modal | Container |
| `clients-table` | dash_table.DataTable | Inside modal |

## KPI output IDs

| ID | What it shows |
|---|---|
| `kpi-revenue` | Money value (e.g. `12 345 678 Br`) |
| `kpi-plan-pct` | Plan completion % |
| `kpi-sales-count` | Count of deals |
| `kpi-avg-check` | Average check |
| `kpi-dynamics` | Dynamics % with color (computed in `fmt_dynamics`) |
| `kpi-dyn-sub` | Dynamics helper text |
| `kpi-clients` | Active client count |
| `kpi-cli-sub` | "X новых / Y старых" subtitle |
| `kpi-rev-label`, `kpi-plan-label`, `kpi-cnt-label`, `kpi-avg-label` | Status-dependent labels from `STATUS_LABELS` |
| `chart-line`, `chart-bar`, `chart-pie` | dcc.Graph `figure` props |
| `data-table` | Detail table `columns` + `data` |
| `insights-list` | 2–3 bullets from `generate_insights` |

## Callbacks

### 1. Manager dropdown visibility — `app.py:843–849`

```python
Output('manager-select-container', 'style'),
Input('role-switcher', 'value')
```

Show only when role == `Менеджер`.

### 2. Main render — `app.py:851–925` (the giant one)

```python
Outputs (16): kpi-revenue, kpi-plan-pct, kpi-sales-count, kpi-avg-check,
              kpi-dynamics, kpi-dyn-sub, kpi-clients, kpi-cli-sub,
              kpi-rev-label, kpi-plan-label, kpi-cnt-label, kpi-avg-label,
              chart-line, chart-bar, chart-pie,
              data-table.columns, data-table.data, insights-list
Inputs  (7):  role-switcher, manager-select, date-picker.start_date,
              date-picker.end_date, type-filter, category-filter, status-filter
```

**Routing:** single function calls `calc_kpis(...)`, `manager_insights(...)`, `monthly_data(...)`, `revenue_by_manager(...)`, `revenue_by_category(...)`, `generate_insights(...)`. Any new filter must:

1. Add a new `dcc` component.
2. Add a new `Input` line to this callback.
3. Extend `filter_data()` with a new clause.
4. Return a 16th-element tuple — **count must match exactly** or Dash raises `IncorrectTypeException`.

### 3. CSV export — `app.py:927–946`

```python
Output('download', 'data'),
Input('export-btn', 'n_clicks'),
State(role, manager, start, end, type, category, status)
```

Exports the currently-filtered `dff` to CSV with `utf-8-sig` encoding.

### 4. Clients modal toggle — `app.py:948–958`

```python
Output('clients-modal', 'is_open'),
Input('btn-clients', 'n_clicks'),
Input('btn-clients-close', 'n_clicks'),
State('clients-modal', 'is_open')
```

Standard pattern: toggle on either button.

### 5. Clients table — `app.py:960–end`

```python
Output('clients-table', 'columns'),
Output('clients-table', 'data'),
Input('btn-clients', 'n_clicks'),
State(role, manager, type-filter)
```

Role-based masking: Директор → all clients; Коммерческий → all; Менеджер → only clients with `ID_менеджера_первой_сделки == manager_id`.

## Adding a new filter — exact diff steps

1. Add a `dcc.Dropdown` / `dcc.RadioItems` next to the existing filters in the filter row layout.
2. Add its `value` to the Inputs list of callback #2 (main render).
3. Add a clause to `filter_data()` (lines 65–82). Mirror the existing `if X and X != 'Все': mask &= ...` pattern.
4. **Do not** modify the return tuple shape — if you don't need a new output, just leave it. Dash is happy with the same number of Outputs.
5. If the filter is role-dependent (e.g. only `Менеджер` sees it), add a parallel visibility callback like #1.
6. Update the `STATUS_LABELS` if the filter changes status-dependent wording (usually it doesn't).

## Common Dash footguns

- **Output count mismatch** — most common. After adding a new `Output` to callback #2, every existing caller must return a tuple of the new size.
- **`no_update` import** — already used; reach for it if a callback should not modify an output.
- **`prevent_initial_call=True`** — for callbacks that shouldn't fire on app boot (e.g. export, modal toggle).
- **Callback context** — `dash.callback_context.triggered_id` tells you which `Input` fired. Useful for buttons that share callbacks.
