"""
app.py — Дашборд отдела продаж «Аксвил» (MVP)
Стек: Dash + Plotly + Pandas + Bootstrap
"""
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import dash
from dash import dcc, html, dash_table, Input, Output, State, no_update, callback
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

# =============================================================================
# ЗАГРУЗКА / ГЕНЕРАЦИЯ ДАННЫХ
# =============================================================================
for f in ['sales.csv', 'plans.csv', 'clients.csv']:
    if not os.path.exists(f):
        from data_prep import generate_sales as _gs, generate_plans as _gp, generate_clients as _gc
        _sales = _gs(2000)
        _plans = _gp()
        _clients = _gc(_sales)
        _sales.to_csv('sales.csv', index=False, encoding='utf-8-sig')
        _plans.to_csv('plans.csv', index=False, encoding='utf-8-sig')
        _clients.to_csv('clients.csv', index=False, encoding='utf-8-sig')
        break

df_sales = pd.read_csv('sales.csv')
df_sales['Дата'] = pd.to_datetime(df_sales['Дата'])
df_plans = pd.read_csv('plans.csv')
df_plans['Месяц'] = pd.to_datetime(df_plans['Месяц'])
df_clients = pd.read_csv('clients.csv')
df_clients['Дата_первой_сделки'] = pd.to_datetime(df_clients['Дата_первой_сделки'])

DATE_MIN = df_sales['Дата'].min()
DATE_MAX = df_sales['Дата'].max()

# Словарь менеджеров для выпадающего списка
MANAGER_OPTIONS = sorted(
    df_sales[['ID_менеджера', 'ФИО_менеджера']].drop_duplicates().to_dict('records'),
    key=lambda x: x['ФИО_менеджера']
)
MANAGER_OPTIONS = [{'label': m['ФИО_менеджера'], 'value': m['ID_менеджера']}
                   for m in MANAGER_OPTIONS]

# =============================================================================
# КОНСТАНТЫ ОФОРМЛЕНИЯ
# =============================================================================
C = {
    'primary':      '#1A365D',
    'secondary':    '#E2E8F0',
    'accent':       '#DD6B20',
    'success':      '#38A169',
    'danger':       '#E53E3E',
    'white':        '#FFFFFF',
    'text':         '#2D3748',
    'muted':        '#718096',
    'bg':           '#F7FAFC',
    'card_border':  '#E2E8F0',
}

# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================
def filter_data(role, manager_id, start_date, end_date, client_type, category, status):
    """Применяет все активные фильтры к данным"""
    mask = pd.Series(True, index=df_sales.index)
    
    if role == 'Менеджер' and manager_id is not None:
        mask &= df_sales['ID_менеджера'] == manager_id
    if start_date:
        mask &= df_sales['Дата'] >= pd.Timestamp(start_date)
    if end_date:
        mask &= df_sales['Дата'] <= pd.Timestamp(end_date)
    if client_type and client_type != 'Все':
        mask &= df_sales['Тип_клиента'] == client_type
    if category and category != 'Все':
        mask &= df_sales['Категория'] == category
    if status and status != 'Все':
        mask &= df_sales['Статус'] == status
    
    return df_sales[mask].copy()

def prorated_plan(role, manager_id, start_date, end_date):
    """Плановая сумма, пропорционально дням в выбранном периоде"""
    if not start_date or not end_date:
        return 0.0
    
    s = pd.Timestamp(start_date)
    e = pd.Timestamp(end_date)
    total = 0.0
    current = s.replace(day=1)
    
    while current <= e:
        m_end = current + pd.offsets.MonthEnd(1)
        overlap_start = max(current, s)
        overlap_end = min(m_end, e)
        days_in_month = m_end.day
        days_overlap = (overlap_end - overlap_start).days + 1
        
        plan_mask = (df_plans['Месяц'] == current)
        if role == 'Менеджер' and manager_id is not None:
            plan_mask &= df_plans['ID_менеджера'] == manager_id
        
        plan_rows = df_plans[plan_mask]
        if not plan_rows.empty:
            total += plan_rows['Плановая_сумма'].sum() * days_overlap / days_in_month
        
        current += pd.offsets.MonthBegin(1)
    
    return total

def calc_kpis(role, manager_id, start_date, end_date, client_type, category, status):
    """Расчёт всех KPI на основе фильтров"""
    df = filter_data(role, manager_id, start_date, end_date, client_type, category, status)
    target = get_target_status(status)
    selected = df[df['Статус'] == target].copy()
    
    revenue = selected['Сумма'].sum() if not selected.empty else 0.0
    sales_count = selected['Номер_договора'].nunique() if not selected.empty else 0
    avg_check = round(revenue / sales_count, 2) if sales_count > 0 else 0.0
    
    # План сравниваем только для оплаченных сделок
    plan_pct = None
    if target == 'Оплачено':
        plan_sum = prorated_plan(role, manager_id, start_date, end_date)
        plan_pct = round((revenue / plan_sum) * 100, 1) if plan_sum > 0 else None
    
    # Динамика к предыдущему периоду той же длины
    dynamics = None
    period_days = None
    if start_date and end_date:
        s = pd.Timestamp(start_date)
        e = pd.Timestamp(end_date)
        period_days = (e - s).days
        if period_days > 0:
            prev_e = s - timedelta(days=1)
            prev_s = prev_e - timedelta(days=period_days)
            prev_df = filter_data(role, manager_id, prev_s, prev_e, client_type, category, status)
            prev_rev = prev_df[prev_df['Статус'] == target]['Сумма'].sum()
            if prev_rev > 0:
                dynamics = round((revenue - prev_rev) / prev_rev * 100, 1)
    
    # Активные и новые клиенты
    active_clients = selected['ID_клиента'].nunique() if not selected.empty else 0
    new_clients = 0
    old_clients = 0
    if not selected.empty:
        active_ids = set(selected['ID_клиента'].unique())
        for cid in active_ids:
            row = df_clients[df_clients['ID_клиента'] == cid]
            if not row.empty and row.iloc[0]['Статус_клиента'] == 'Новый':
                new_clients += 1
            else:
                old_clients += 1
    
    return {
        'revenue': revenue,
        'plan_pct': plan_pct,
        'sales_count': sales_count,
        'avg_check': avg_check,
        'dynamics': dynamics,
        'active_clients': active_clients,
        'new_clients': new_clients,
        'old_clients': old_clients,
        'df': df,
        'paid': selected,
    }

def fmt_money(v):
    """Форматирует число в белорусские рубли: 12 345 678 Br"""
    if v is None or (isinstance(v, float) and v == 0.0):
        return '0 Br'
    return f"{v:,.0f} Br".replace(',', ' ')

def fmt_pct(v):
    """Форматирует процент"""
    if v is None:
        return '—'
    return f"{v:.1f}%"

def fmt_dynamics(v):
    """Форматирует динамику с цветом: +15.3% / -5.2% / —"""
    if v is None:
        return '—', C['muted']
    if v > 0:
        return f"+{v:.1f}%", C['success']
    elif v < 0:
        return f"{v:.1f}%", C['danger']
    else:
        return "0.0%", C['muted']


def get_target_status(status_filter):
    return status_filter if status_filter and status_filter != 'Все' else 'Оплачено'


STATUS_LABELS = {
    'Оплачено': {'rev': 'Выручка', 'plan': 'Выполнение плана', 'cnt': 'Продажи', 'avg': 'Средний чек', 'line': 'Динамика выручки и плана', 'bar': 'По менеджерам', 'pie': 'Доля категорий'},
    'В работе': {'rev': 'Сумма в работе', 'plan': '—', 'cnt': 'Заказов в работе', 'avg': 'Средняя сумма',  'line': 'Динамика заказов в работе', 'bar': 'Заказы в работе по менеджерам', 'pie': 'Доля категорий (в работе)'},
    'Отменено': {'rev': 'Сумма отменённых', 'plan': '—', 'cnt': 'Отменённых заказов', 'avg': 'Средняя сумма', 'line': 'Динамика отменённых заказов', 'bar': 'Отмены по менеджерам', 'pie': 'Доля категорий (отменено)'},
    'Отозвано': {'rev': 'Сумма отозванных', 'plan': '—', 'cnt': 'Отозванных заказов', 'avg': 'Средняя сумма', 'line': 'Динамика отозванных заказов', 'bar': 'Отозывы по менеджерам', 'pie': 'Доля категорий (отозвано)'},
}


def monthly_data(role, manager_id, start_date, end_date, client_type, category, status):
    """DataFrame с суммой и планом по месяцам (для line chart)"""
    df = filter_data(role, manager_id, start_date, end_date, client_type, category, status)
    target = get_target_status(status)
    selected = df[df['Статус'] == target].copy()
    
    if selected.empty:
        return pd.DataFrame()
    
    selected['Месяц'] = selected['Дата'].dt.to_period('M').dt.start_time
    monthly_rev = selected.groupby('Месяц')['Сумма'].sum().reset_index()
    monthly_rev.columns = ['Месяц', 'Сумма_показатель']
    
    # План показываем только для оплаченных сделок
    if target == 'Оплачено':
        months = monthly_rev['Месяц'].unique()
        plan_mask = df_plans['Месяц'].isin(months)
        if role == 'Менеджер' and manager_id is not None:
            plan_mask &= df_plans['ID_менеджера'] == manager_id
        monthly_plan = df_plans[plan_mask].groupby('Месяц')['Плановая_сумма'].sum().reset_index()
        monthly_plan.columns = ['Месяц', 'План']
        result = pd.merge(monthly_rev, monthly_plan, on='Месяц', how='outer').fillna(0)
    else:
        result = monthly_rev
        result['План'] = 0
    
    result = result.sort_values('Месяц').reset_index(drop=True)
    return result

def revenue_by_manager(role, manager_id, start_date, end_date, client_type, category, status):
    """Сумма в разрезе менеджеров (для bar chart)"""
    df = filter_data(role, manager_id, start_date, end_date, client_type, category, status)
    target = get_target_status(status)
    selected = df[df['Статус'] == target]
    
    if selected.empty:
        return pd.DataFrame()
    
    return selected.groupby('ФИО_менеджера')['Сумма'].sum().reset_index()\
        .sort_values('Сумма', ascending=False).reset_index(drop=True)

def revenue_by_category(role, manager_id, start_date, end_date, client_type, category, status):
    """Сумма по категориям (для pie chart)"""
    df = filter_data(role, manager_id, start_date, end_date, client_type, category, status)
    target = get_target_status(status)
    selected = df[df['Статус'] == target]
    
    if selected.empty:
        return pd.DataFrame()
    
    return selected.groupby('Категория')['Сумма'].sum().reset_index()\
        .sort_values('Сумма', ascending=False).reset_index(drop=True)

def generate_insights(kpis):
    """Формирует 2-3 буллита с выводами"""
    bullets = []
    
    # 1. План
    pp = kpis['plan_pct']
    if pp is not None:
        if pp >= 100:
            bullets.append(f"План перевыполнен на {pp - 100:.1f}%")
        else:
            bullets.append(f"План выполнен на {pp:.1f}%")
    else:
        bullets.append("План на выбранный период не задан")
    
    # 2. Лучший менеджер по выручке
    bm = kpis.get('best_manager')
    wm = kpis.get('worst_manager')
    if bm and bm['revenue'] > 0:
        bullets.append(f"Лучший результат — {bm['name']} ({fmt_money(bm['revenue'])})")
    if wm and wm.get('pct') is not None and wm['pct'] < 100:
        bullets.append(f"Наибольшее отставание от плана — {wm['name']} ({fmt_pct(wm['pct'])})")
    
    # 3. Динамика
    dyn = kpis['dynamics']
    if dyn is not None:
        if dyn > 0:
            bullets.append(f"Рост выручки к предыдущему периоду на {dyn:.1f}%")
        elif dyn < 0:
            bullets.append(f"Снижение выручки к предыдущему периоду на {abs(dyn):.1f}%")
        else:
            bullets.append("Выручка не изменилась относительно предыдущего периода")
    
    if not bullets:
        bullets.append("Недостаточно данных для анализа")
    
    return bullets

def manager_insights(kpis, role, manager_id, start_date, end_date, client_type, category, status):
    """Дополняет kpis данными о менеджерах (best/worst)"""
    df = filter_data(role, manager_id, start_date, end_date, client_type, category, status)
    target = get_target_status(status)
    selected = df[df['Статус'] == target]
    
    if selected.empty:
        kpis['best_manager'] = None
        kpis['worst_manager'] = None
        return kpis
    
    mgr_rev = selected.groupby(['ID_менеджера', 'ФИО_менеджера'])['Сумма'].sum().reset_index()
    mgr_rev.columns = ['id', 'name', 'revenue']
    
    # Сравнение с планом — только для оплаченных сделок
    if target == 'Оплачено':
        s = pd.Timestamp(start_date) if start_date else DATE_MIN
        e = pd.Timestamp(end_date) if end_date else DATE_MAX
        all_months = pd.date_range(s.replace(day=1), e, freq='MS')
        plan_m = df_plans[df_plans['Месяц'].isin(all_months)]
        mgr_plan = plan_m.groupby('ID_менеджера')['Плановая_сумма'].sum().reset_index()
        mgr_plan.columns = ['id', 'plan']
        
        merged = mgr_rev.merge(mgr_plan, on='id', how='left')
        merged['pct'] = merged.apply(
            lambda r: (r['revenue'] / r['plan']) * 100 if r['plan'] > 0 else None, axis=1
        )
        
        if not merged.empty:
            best = merged.loc[merged['revenue'].idxmax()]
            kpis['best_manager'] = {'name': best['name'], 'revenue': best['revenue']}
            worst_pct = merged[merged['pct'].notna()]
            if not worst_pct.empty:
                w = worst_pct.loc[worst_pct['pct'].idxmin()]
                kpis['worst_manager'] = {'name': w['name'], 'pct': w['pct']}
            else:
                kpis['worst_manager'] = None
        else:
            kpis['best_manager'] = None
            kpis['worst_manager'] = None
    else:
        # Без плана — просто лучший по сумме
        if not mgr_rev.empty:
            best = mgr_rev.loc[mgr_rev['revenue'].idxmax()]
            kpis['best_manager'] = {'name': best['name'], 'revenue': best['revenue']}
        else:
            kpis['best_manager'] = None
        kpis['worst_manager'] = None
    
    return kpis

# =============================================================================
# ПОСТРОЕНИЕ ГРАФИКОВ
# =============================================================================
CHART_LAYOUT = dict(
    font_family='Inter, Roboto, system-ui, sans-serif',
    font_color=C['text'],
    paper_bgcolor=C['white'],
    plot_bgcolor=C['white'],
    hovermode='x unified',
    xaxis=dict(gridcolor=C['secondary'], zerolinecolor=C['secondary']),
    yaxis=dict(gridcolor=C['secondary'], zerolinecolor=C['secondary']),
    margin=dict(l=40, r=20, t=40, b=40),
    legend=dict(orientation='h', y=-0.25),
)

def empty_fig(msg='Нет данных'):
    """Пустой график с сообщением"""
    fig = go.Figure()
    fig.add_annotation(text=msg, x=0.5, y=0.5, xref='paper', yref='paper',
                       showarrow=False, font=dict(size=16, color=C['muted']))
    fig.update_layout(**CHART_LAYOUT)
    return fig

def create_line_chart(monthly, title='Динамика', show_plan=True):
    if monthly is None or monthly.empty:
        return empty_fig()
    
    fig = go.Figure()
    col_name = 'Выручка' if 'Выручка' in monthly.columns else 'Сумма_показатель'
    fig.add_trace(go.Scatter(
        x=monthly['Месяц'], y=monthly[col_name],
        mode='lines+markers', name=col_name,
        line=dict(color=C['primary'], width=3),
        marker=dict(size=8, color=C['primary']),
        hovertemplate='%{y:,.0f} Br<extra>' + col_name + '</extra>'
    ))
    
    if show_plan and 'План' in monthly.columns and monthly['План'].sum() > 0:
        fig.add_trace(go.Scatter(
            x=monthly['Месяц'], y=monthly['План'],
            mode='lines+markers', name='План',
            line=dict(color=C['accent'], width=3, dash='dash'),
            marker=dict(size=8, color=C['accent']),
            hovertemplate='%{y:,.0f} Br<extra>План</extra>'
        ))
    
    fig.update_layout(
        title=title,
        yaxis_title='Сумма, Br',
        **CHART_LAYOUT
    )
    fig.update_xaxes(dtick='M1', tickformat='%b %Y')
    return fig

def create_bar_chart(data, title='По менеджерам'):
    if data is None or data.empty:
        return empty_fig()
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=data['ФИО_менеджера'], y=data['Сумма'],
        marker_color=C['primary'],
        text=data['Сумма'].apply(lambda v: f"{v:,.0f} Br".replace(',', ' ')),
        textposition='outside',
        hovertemplate='%{y:,.0f} Br<extra></extra>'
    ))
    
    fig.update_layout(
        title=title,
        yaxis_title='Сумма, Br',
        xaxis_tickangle=-20,
        **CHART_LAYOUT
    )
    return fig

def create_pie_chart(data, title='Доля категорий'):
    if data is None or data.empty:
        return empty_fig()
    
    colors = [C['primary'], C['accent'], C['success'], '#718096']
    fig = go.Figure(data=[go.Pie(
        labels=data['Категория'], values=data['Сумма'],
        hole=0.4,
        marker=dict(colors=colors[:len(data)]),
        textinfo='label+percent',
        hovertemplate='%{label}<br>%{value:,.0f} Br (%{percent})<extra></extra>'
    )])
    
    fig.update_layout(
        title=title,
        **CHART_LAYOUT
    )
    return fig

def prepare_table_data(df):
    """Подготавливает данные для dash_table с форматированием"""
    if df.empty:
        return [], []
    
    cols = [
        {'name': 'Дата', 'id': 'Дата'},
        {'name': 'Номер договора', 'id': 'Номер_договора'},
        {'name': 'Клиент', 'id': 'Название_клиента'},
        {'name': 'Тип', 'id': 'Тип_клиента'},
        {'name': 'Менеджер', 'id': 'ФИО_менеджера'},
        {'name': 'Категория', 'id': 'Категория'},
        {'name': 'Кол-во', 'id': 'Количество'},
        {'name': 'Цена за ед.', 'id': 'Цена_за_ед'},
        {'name': 'Сумма', 'id': 'Сумма'},
        {'name': 'Статус', 'id': 'Статус'},
    ]
    
    out = df.copy()
    out['Дата'] = out['Дата'].dt.strftime('%d.%m.%Y')
    out['Сумма'] = out['Сумма'].apply(lambda v: f"{v:,.0f} Br".replace(',', ' '))
    out['Цена_за_ед'] = out['Цена_за_ед'].apply(lambda v: f"{v:,.2f}".replace(',', ' '))
    
    return cols, out.to_dict('records')

# =============================================================================
# ИНИЦИАЛИЗАЦИЯ DASH
# =============================================================================
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = 'Аксвил — Дашборд продаж'

# -----------------------------------------------------------------------------
# Кастомный CSS
# -----------------------------------------------------------------------------
CUSTOM_CSS = f"""
body {{
    background-color: {C['bg']};
    font-family: Inter, Roboto, system-ui, sans-serif;
    color: {C['text']};
}}
.kpi-card {{
    border-radius: 10px;
    border: 1px solid {C['card_border']};
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    transition: box-shadow 0.2s;
    background: {C['white']};
}}
.kpi-card:hover {{
    box-shadow: 0 4px 12px rgba(0,0,0,0.10);
}}
.kpi-label {{
    color: {C['primary']};
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 6px;
    text-align: center;
}}
.kpi-value {{
    font-size: 1.6rem;
    font-weight: 800;
    line-height: 1.2;
    color: {C['accent']};
    text-align: center;
}}
.kpi-sub {{
    text-align: center;
}}
.kpi-sub {{
    font-size: 0.8rem;
    color: {C['muted']};
    margin-top: 2px;
}}
.filter-section {{
    background: {C['white']};
    border-radius: 10px;
    border: 1px solid {C['card_border']};
    padding: 16px 20px;
    margin-bottom: 16px;
}}
.insights-box {{
    background: {C['white']};
    border-radius: 10px;
    border: 1px solid {C['card_border']};
    padding: 16px 20px;
    margin-top: 16px;
}}
.insights-box ul {{
    margin-bottom: 0;
    padding-left: 20px;
}}
.insights-box li {{
    margin-bottom: 6px;
    font-size: 0.95rem;
}}
.chart-container {{
    background: {C['white']};
    border-radius: 10px;
    border: 1px solid {C['card_border']};
    padding: 8px;
    margin-bottom: 16px;
}}
"""

# Применяем кастомный CSS
app.index_string = app.index_string.replace(
    '</head>',
    f'<style>{CUSTOM_CSS}</style></head>'
)

# =============================================================================
# LAYOUT
# =============================================================================

# --- Шапка ---
navbar = dbc.Navbar(
    dbc.Container([
        html.Div([
            html.Span('Аксвил', style={'fontWeight': 800, 'fontSize': '1.2rem', 'color': C['white']}),
            html.Span(' — Дашборд продаж', style={'fontSize': '1rem', 'color': C['secondary'], 'marginLeft': 6}),
        ]),
        html.Div([
            html.Span('Роль:', style={'color': C['secondary'], 'marginRight': 10, 'fontSize': '0.9rem'}),
            dcc.RadioItems(
                id='role-switcher',
                options=[
                    {'label': ' Директор', 'value': 'Директор'},
                    {'label': ' Ком. директор', 'value': 'КО'},
                    {'label': ' Менеджер', 'value': 'Менеджер'},
                ],
                value='Директор',
                inline=True,
                labelStyle={
                    'color': C['secondary'], 'marginRight': 16, 'cursor': 'pointer',
                    'fontSize': '0.9rem'
                },
                inputStyle={'marginRight': 4},
            ),
        ], style={'display': 'flex', 'alignItems': 'center', 'marginLeft': 'auto'}),
    ], fluid=True),
    color=C['primary'],
    dark=True,
    className='mb-3',
    style={'padding': '8px 0'},
)

# --- Контейнер для выбора менеджера (появляется при роли Менеджер) ---
manager_select_div = html.Div(
    id='manager-select-container',
    children=dbc.Row([
        dbc.Col(html.Label('Выберите менеджера:', style={'fontWeight': 600}), width='auto'),
        dbc.Col(dcc.Dropdown(
            id='manager-select',
            options=MANAGER_OPTIONS,
            value=MANAGER_OPTIONS[0]['value'] if MANAGER_OPTIONS else None,
            clearable=False,
            style={'minWidth': 220}
        ), width='auto'),
    ], align='center', className='mb-3'),
    style={'display': 'none'}
)

# --- Фильтры ---
filters_section = html.Div([
    dbc.Row([
        dbc.Col([
            html.Label('Период', style={'fontWeight': 600, 'fontSize': '0.85rem'}),
            dcc.DatePickerRange(
                id='date-picker',
                min_date_allowed=DATE_MIN,
                max_date_allowed=DATE_MAX,
                start_date=DATE_MIN,
                end_date=DATE_MAX,
                display_format='DD.MM.YYYY',
                className='w-100',
            ),
        ], xs=12, md=4),
        dbc.Col([
            html.Label('Тип клиента', style={
                'fontWeight': 700, 'fontSize': '0.85rem', 'color': C['primary'],
                'display': 'block', 'textAlign': 'center', 'marginBottom': 4
            }),
            dcc.Dropdown(
                id='type-filter',
                options=[
                    {'label': 'Все', 'value': 'Все'},
                    {'label': 'Опт', 'value': 'Опт'},
                    {'label': 'Розница', 'value': 'Розница'},
                ],
                value='Все', clearable=False,
            ),
        ], xs=6, md=2),
        dbc.Col([
            html.Label('Категория', style={
                'fontWeight': 700, 'fontSize': '0.85rem', 'color': C['primary'],
                'display': 'block', 'textAlign': 'center', 'marginBottom': 4
            }),
            dcc.Dropdown(
                id='category-filter',
                options=[
                    {'label': 'Все', 'value': 'Все'},
                    {'label': 'Трубы', 'value': 'Трубы'},
                    {'label': 'Лист', 'value': 'Лист'},
                    {'label': 'Арматура', 'value': 'Арматура'},
                    {'label': 'Метизы', 'value': 'Метизы'},
                ],
                value='Все', clearable=False,
            ),
        ], xs=6, md=2),
        dbc.Col([
            html.Label('Статус сделки', style={
                'fontWeight': 700, 'fontSize': '0.85rem', 'color': C['primary'],
                'display': 'block', 'textAlign': 'center', 'marginBottom': 4
            }),
            dcc.Dropdown(
                id='status-filter',
                options=[
                    {'label': 'Все', 'value': 'Все'},
                    {'label': 'Оплачено', 'value': 'Оплачено'},
                    {'label': 'В работе', 'value': 'В работе'},
                    {'label': 'Отменено', 'value': 'Отменено'},
                    {'label': 'Отозвано', 'value': 'Отозвано'},
                ],
                value='Все', clearable=False,
            ),
        ], xs=6, md=2),
    ], className='g-2'),
], className='filter-section')

# --- KPI-карточки ---
def kpi_card(cid, label, value_id, sub=None, val_color=None):
    return dbc.Col([
        dbc.Card([
            dbc.CardBody([
                html.Div(label, className='kpi-label', id=cid+'-label'),
                html.Div(id=value_id, className='kpi-value',
                         style={'color': val_color} if val_color else {}),
                html.Div(id=cid+'-sub', className='kpi-sub') if sub else None,
            ], style={'padding': '12px 14px'}),
        ], className='kpi-card h-100'),
    ], xs=6, md=4, lg=2)

kpi_row = dbc.Row([
    kpi_card('kpi-rev', 'Выручка', 'kpi-revenue'),
    kpi_card('kpi-plan', 'Выполнение плана', 'kpi-plan-pct'),
    kpi_card('kpi-cnt', 'Продажи', 'kpi-sales-count'),
    kpi_card('kpi-avg', 'Средний чек', 'kpi-avg-check'),
    kpi_card('kpi-dyn', 'Динамика', 'kpi-dynamics', sub=True),
    dbc.Col([
        dbc.Card([
            dbc.CardBody([
                html.Div('Клиенты', className='kpi-label', id='kpi-cli-label'),
                html.Div(id='kpi-clients', className='kpi-value'),
                html.Div(id='kpi-cli-sub', className='kpi-sub'),
                html.Hr(style={'margin': '6px 0 4px 0'}),
                dbc.Button(
                    'Просмотр базы клиентов', id='btn-clients',
                    color='primary', size='sm', outline=True,
                    style={'fontSize': '0.7rem', 'padding': '2px 8px', 'width': '100%'}
                ),
            ], style={'padding': '12px 14px'}),
        ], className='kpi-card h-100'),
    ], xs=6, md=4, lg=2),
], className='g-2 mb-3')

# --- Графики ---
charts_row1 = dbc.Row([
    dbc.Col([
        html.Div(dcc.Graph(id='chart-line', config={'displayModeBar': False}),
                 className='chart-container'),
    ], xs=12),
], className='mb-2')

charts_row2 = dbc.Row([
    dbc.Col([
        html.Div(dcc.Graph(id='chart-bar', config={'displayModeBar': False}),
                 className='chart-container'),
    ], xs=12, md=6),
    dbc.Col([
        html.Div(dcc.Graph(id='chart-pie', config={'displayModeBar': False}),
                 className='chart-container'),
    ], xs=12, md=6),
], className='mb-3')

# --- Таблица ---
table_section = html.Div([
    html.H5('Детализация по сделкам', style={'marginBottom': 8, 'fontWeight': 600}),
    dash_table.DataTable(
        id='data-table',
        columns=[],
        data=[],
        sort_action='native',
        page_size=10,
        style_table={'overflowX': 'auto', 'borderRadius': 8},
        style_header={
            'backgroundColor': C['primary'],
            'color': 'white',
            'fontWeight': 600,
            'fontSize': '0.85rem',
            'whiteSpace': 'normal',
        },
        style_cell={
            'fontFamily': 'Inter, Roboto, sans-serif',
            'fontSize': '0.85rem',
            'padding': '6px 10px',
            'textAlign': 'left',
        },
        style_data_conditional=[
            {'if': {'filter_query': '{Статус} = "Оплачено"'}, 'backgroundColor': '#F0FFF4'},
            {'if': {'filter_query': '{Статус} = "В работе"'}, 'backgroundColor': '#FFFAF0'},
            {'if': {'filter_query': '{Статус} = "Отменено"'}, 'backgroundColor': '#FFF5F5'},
            {'if': {'filter_query': '{Статус} = "Отозвано"'}, 'backgroundColor': '#F0F0F0', 'color': '#718096'},
        ],
    ),
], className='filter-section')

# --- Выводы ---
insights_section = html.Div([
    html.H5('Аналитические выводы', style={'marginBottom': 8, 'fontWeight': 600}),
    html.Ul(id='insights-list', style={'marginBottom': 0}),
], className='insights-box')

# --- Экспорт ---
export_section = html.Div([
    html.Hr(style={'margin': '16px 0'}),
    dbc.Row([
        dbc.Col(dbc.Button(
            'Экспорт в CSV', id='export-btn', color='primary',
            outline=True, n_clicks=0, className='me-2'
        ), width='auto'),
        dbc.Col(html.Small(
            'Выгружаются данные с учётом текущих фильтров',
            style={'color': C['muted'], 'lineHeight': '38px'}
        ), width='auto'),
    ], align='center'),
    dcc.Download(id='download'),
], style={'marginTop': 8, 'marginBottom': 24})

# --- Модальное окно базы клиентов ---
clients_modal = dbc.Modal(
    [
        dbc.ModalHeader(dbc.ModalTitle('База клиентов')),
        dbc.ModalBody([
            html.Div(id='clients-table-container', children=[
                dash_table.DataTable(
                    id='clients-table',
                    columns=[],
                    data=[],
                    sort_action='native',
                    page_size=15,
                    style_table={'overflowX': 'auto'},
                    style_header={
                        'backgroundColor': C['primary'],
                        'color': 'white',
                        'fontWeight': 600,
                        'fontSize': '0.8rem',
                        'whiteSpace': 'normal',
                    },
                    style_cell={
                        'fontFamily': 'Inter, Roboto, sans-serif',
                        'fontSize': '0.8rem',
                        'padding': '4px 8px',
                    },
                    style_data_conditional=[
                        {'if': {'filter_query': '{Статус_клиента} = "Новый"'}, 'backgroundColor': '#EBF8FF'},
                        {'if': {'filter_query': '{Статус_клиента} = "Старый"'}, 'backgroundColor': '#F0FFF4'},
                    ],
                ),
            ]),
        ]),
        dbc.ModalFooter(
            dbc.Button('Закрыть', id='btn-clients-close', className='ms-auto', n_clicks=0)
        ),
    ],
    id='clients-modal',
    size='xl',
    scrollable=True,
    is_open=False,
)

# --- Сборка layout ---
app.layout = dbc.Container([
    navbar,
    dbc.Container([
        manager_select_div,
        filters_section,
        kpi_row,
        charts_row1,
        charts_row2,
        table_section,
        insights_section,
        export_section,
        clients_modal,
    ], fluid=True),
], fluid=True, style={'padding': 0})

# =============================================================================
# CALLBACKS
# =============================================================================

# ---- Переключение видимости выбора менеджера ----
@app.callback(
    Output('manager-select-container', 'style'),
    Input('role-switcher', 'value'),
)
def toggle_manager(role):
    if role == 'Менеджер':
        return {'display': 'block'}
    return {'display': 'none'}

# ---- Основной callback обновления дашборда ----
@app.callback(
    Output('kpi-revenue', 'children'),
    Output('kpi-plan-pct', 'children'),
    Output('kpi-sales-count', 'children'),
    Output('kpi-avg-check', 'children'),
    Output('kpi-dynamics', 'children'),
    Output('kpi-dyn-sub', 'children'),
    Output('kpi-clients', 'children'),
    Output('kpi-cli-sub', 'children'),
    Output('kpi-rev-label', 'children'),
    Output('kpi-plan-label', 'children'),
    Output('kpi-cnt-label', 'children'),
    Output('kpi-avg-label', 'children'),
    Output('chart-line', 'figure'),
    Output('chart-bar', 'figure'),
    Output('chart-pie', 'figure'),
    Output('data-table', 'columns'),
    Output('data-table', 'data'),
    Output('insights-list', 'children'),
    Input('role-switcher', 'value'),
    Input('manager-select', 'value'),
    Input('date-picker', 'start_date'),
    Input('date-picker', 'end_date'),
    Input('type-filter', 'value'),
    Input('category-filter', 'value'),
    Input('status-filter', 'value'),
)
def update_dashboard(role, manager, s_date, e_date, ctype, cat, status):
    tgt = get_target_status(status)
    lbl = STATUS_LABELS.get(tgt, STATUS_LABELS['Оплачено'])

    kpis = calc_kpis(role, manager, s_date, e_date, ctype, cat, status)
    kpis = manager_insights(kpis, role, manager, s_date, e_date, ctype, cat, status)
    
    kpi_rev = fmt_money(kpis['revenue'])
    kpi_plan = fmt_pct(kpis['plan_pct'])
    kpi_cnt = f"{kpis['sales_count']}" if kpis['sales_count'] > 0 else '—'
    kpi_avg = fmt_money(kpis['avg_check']) if kpis['avg_check'] > 0 else '—'
    
    dyn_text, dyn_color = fmt_dynamics(kpis['dynamics'])
    dyn_sub = '' if dyn_text == '—' else 'к пред. периоду'
    
    cli_text = f"{kpis['active_clients']}" if kpis['active_clients'] > 0 else '—'
    cli_sub = f"новых: {kpis['new_clients']}, старых: {kpis['old_clients']}" if kpis['active_clients'] > 0 else ''
    
    md = monthly_data(role, manager, s_date, e_date, ctype, cat, status)
    show_plan = tgt == 'Оплачено'
    line_fig = create_line_chart(md, title=lbl['line'], show_plan=show_plan)
    
    bd = revenue_by_manager(role, manager, s_date, e_date, ctype, cat, status)
    bar_fig = create_bar_chart(bd, title=lbl['bar'])
    
    pd_ = revenue_by_category(role, manager, s_date, e_date, ctype, cat, status)
    pie_fig = create_pie_chart(pd_, title=lbl['pie'])
    
    df_filtered = filter_data(role, manager, s_date, e_date, ctype, cat, status)
    cols, tbl_data = prepare_table_data(df_filtered)
    
    insights = generate_insights(kpis)
    insights_items = [html.Li(t) for t in insights]
    
    return (
        kpi_rev, kpi_plan, kpi_cnt, kpi_avg,
        html.Span(dyn_text, style={'color': dyn_color}),
        dyn_sub,
        cli_text, cli_sub,
        lbl['rev'], lbl['plan'], lbl['cnt'], lbl['avg'],
        line_fig, bar_fig, pie_fig,
        cols, tbl_data,
        insights_items,
    )

# ---- Экспорт в CSV ----
@app.callback(
    Output('download', 'data'),
    Input('export-btn', 'n_clicks'),
    State('role-switcher', 'value'),
    State('manager-select', 'value'),
    State('date-picker', 'start_date'),
    State('date-picker', 'end_date'),
    State('type-filter', 'value'),
    State('category-filter', 'value'),
    State('status-filter', 'value'),
    prevent_initial_call=True,
)
def export_csv(n_clicks, role, manager, s_date, e_date, ctype, cat, status):
    if not n_clicks:
        return no_update
    
    df = filter_data(role, manager, s_date, e_date, ctype, cat, status)
    csv_str = df.to_csv(index=False, encoding='utf-8-sig')
    return dict(content=csv_str, filename='sales_export.csv')

# ---- Открытие/закрытие модального окна клиентов ----
@app.callback(
    Output('clients-modal', 'is_open'),
    Input('btn-clients', 'n_clicks'),
    Input('btn-clients-close', 'n_clicks'),
    State('clients-modal', 'is_open'),
)
def toggle_clients_modal(n1, n2, is_open):
    if n1 or n2:
        return not is_open
    return is_open


# ---- Заполнение таблицы клиентов ----
@app.callback(
    Output('clients-table', 'columns'),
    Output('clients-table', 'data'),
    Input('btn-clients', 'n_clicks'),
    State('role-switcher', 'value'),
    State('manager-select', 'value'),
    State('type-filter', 'value'),
)
def update_clients_table(n_clicks, role, manager_id, client_type):
    if not n_clicks:
        return [], []

    tab = df_clients.copy()
    if role == 'Менеджер' and manager_id is not None:
        tab = tab[tab['ID_менеджера_первой_сделки'] == manager_id]
    if client_type and client_type != 'Все':
        tab = tab[tab['Тип_клиента'] == client_type]

    if tab.empty:
        cols = [{'name': c, 'id': c} for c in tab.columns]
        return cols, []

    tab['Дата_первой_сделки'] = tab['Дата_первой_сделки'].dt.strftime('%d.%m.%Y')
    tab['Общая_сумма'] = tab['Общая_сумма'].apply(
        lambda v: f"{v:,.0f} Br".replace(',', ' ')
    )
    tab['Оплачено'] = tab['Оплачено'].astype(int)
    tab['Отменено'] = tab['Отменено'].astype(int)

    cols = [
        {'name': 'ID', 'id': 'ID_клиента'},
        {'name': 'Клиент', 'id': 'Название_клиента'},
        {'name': 'Тип', 'id': 'Тип_клиента'},
        {'name': 'Статус', 'id': 'Статус_клиента'},
        {'name': 'Менеджер', 'id': 'Менеджер_первой_сделки'},
        {'name': 'Первая сделка', 'id': 'Дата_первой_сделки'},
        {'name': 'Всего сделок', 'id': 'Всего_сделок'},
        {'name': 'Оплачено', 'id': 'Оплачено'},
        {'name': 'Отменено', 'id': 'Отменено'},
        {'name': 'Общая сумма', 'id': 'Общая_сумма'},
    ]
    return cols, tab.to_dict('records')


# =============================================================================
# ЗАПУСК
# =============================================================================
if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=8050)
