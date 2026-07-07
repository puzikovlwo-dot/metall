"""
data_prep.py — Генерация тестовых данных для дашборда «Аксвил»
"""
import pandas as pd
import numpy as np

np.random.seed(42)


def generate_sales(n=2000, start='2026-01-01', end='2026-06-30'):
    start = pd.Timestamp(start)
    end = pd.Timestamp(end)

    managers = {
        1: 'Иванов А.А.', 2: 'Петров Б.В.', 3: 'Сидоров В.Г.',
        4: 'Кузнецов Д.Е.', 5: 'Соколова Е.Д.'
    }

    # Специализация менеджеров по типам клиентов и категориям
    # (manager_id): {client_type_bias, category_bias}
    manager_specialization = {
        1: {'type': 'Опт',     'cat': 'Трубы'},     # Иванов — опт, трубы
        2: {'type': None,      'cat': None},         # Петров — универсал
        3: {'type': 'Розница', 'cat': 'Арматура'},  # Сидоров — розница, арматура
        4: {'type': 'Розница', 'cat': 'Метизы'},    # Кузнецов — розница, метизы
        5: {'type': 'Опт',     'cat': 'Лист'},       # Соколова — опт, лист
    }

    n_clients = 200
    client_ids = np.arange(1, n_clients + 1)

    # Типы клиентов: 35% опт, 65% розница
    client_type_map = {}
    for cid in client_ids:
        client_type_map[cid] = np.random.choice(['Опт', 'Розница'], p=[0.35, 0.65])

    # Привязка клиентов к менеджерам (с учётом специализации)
    client_manager_map = {}
    for cid in client_ids:
        ct = client_type_map[cid]
        # Выбираем менеджера, который подходит под тип клиента (если есть специализация)
        candidates = [mid for mid, spec in manager_specialization.items()
                      if spec['type'] is None or spec['type'] == ct]
        client_manager_map[cid] = np.random.choice(candidates)

    # Названия клиентов
    client_name_map = {}
    opt_companies = [
        'СтальПром', 'МеталлИнвест', 'ТрубТорг', 'АрмСтрой', 'ЛистМет',
        'ПрофМет', 'УралСталь', 'СибМет', 'ВолгаМет', 'ДонСталь',
        'КавказМет', 'ЦентрСталь', 'СеверСталь', 'ЮгМет', 'ВостокМет',
        'БелМеталл', 'МетСнаб', 'СтальИндустрия', 'ТрубМаркет', 'АрмТорг'
    ]
    retail_last = [
        'Иванов', 'Петров', 'Сидоров', 'Кузнецов', 'Соколов',
        'Попов', 'Лебедев', 'Козлов', 'Новиков', 'Морозов',
        'Волков', 'Зайцев', 'Соловьев', 'Васильев', 'Федоров',
        'Ковалев', 'Павлов', 'Семенов', 'Егоров', 'Тимофеев'
    ]
    retail_first = [
        'Иван', 'Петр', 'Сергей', 'Андрей', 'Алексей',
        'Дмитрий', 'Николай', 'Михаил', 'Владимир', 'Александр',
        'Елена', 'Ольга', 'Наталья', 'Татьяна', 'Светлана',
        'Ирина', 'Анна', 'Мария', 'Екатерина', 'Ксения'
    ]

    for i, cid in enumerate(client_ids):
        if client_type_map[cid] == 'Опт':
            company = opt_companies[i % len(opt_companies)]
            client_name_map[cid] = f"ООО «{company}-{cid:03d}»"
        else:
            ln = retail_last[i % len(retail_last)]
            fn = retail_first[(i // len(retail_last)) % len(retail_first)]
            client_name_map[cid] = f"{ln} {fn}."

    # Категории товаров и их параметры
    categories = {
        'Трубы':   {'price': (300, 1200), 'qty_opt': (50, 500),  'qty_ret': (1, 15)},
        'Лист':    {'price': (200, 900),  'qty_opt': (30, 300),  'qty_ret': (1, 10)},
        'Арматура':{'price': (150, 700),  'qty_opt': (100, 1000),'qty_ret': (3, 30)},
        'Метизы':  {'price': (20, 250),   'qty_opt': (200, 2000),'qty_ret': (5, 80)},
    }

    # Матрица вероятностей статусов в зависимости от (тип_клиента, категория)
    # Порядок: [Оплачено, В работе, Отменено, Отозвано]
    status_matrix = {
        ('Опт', 'Трубы'):     [0.82, 0.10, 0.05, 0.03],
        ('Опт', 'Лист'):      [0.72, 0.17, 0.07, 0.04],
        ('Опт', 'Арматура'):  [0.78, 0.13, 0.06, 0.03],
        ('Опт', 'Метизы'):    [0.62, 0.25, 0.08, 0.05],
        ('Розница', 'Трубы'): [0.55, 0.24, 0.12, 0.09],
        ('Розница', 'Лист'):  [0.48, 0.28, 0.14, 0.10],
        ('Розница', 'Арматура'): [0.58, 0.22, 0.12, 0.08],
        ('Розница', 'Метизы'):   [0.63, 0.20, 0.10, 0.07],
    }
    statuses = ['Оплачено', 'В работе', 'Отменено', 'Отозвано']

    # Сезонные веса для месяцев (индекс 0 = январь)
    # В Беларуси: янв — затишье, март — квартал, май — праздники, июнь — полугодие
    monthly_weights = [0.7, 0.9, 1.2, 1.0, 0.8, 1.3]

    dates_all = pd.date_range(start, end, freq='D')
    # Вес каждого дня с учётом месяца
    date_weights = np.array([
        monthly_weights[d.month - 1] for d in dates_all
    ])
    date_weights = date_weights / date_weights.sum()

    # Веса клиентов (Pareto — 20% клиентов дают 80% продаж)
    client_weights = np.random.exponential(1, n_clients)
    client_weights /= client_weights.sum()

    # Веса категорий (неравномерный спрос)
    cat_weights = {'Трубы': 0.35, 'Арматура': 0.30, 'Лист': 0.20, 'Метизы': 0.15}

    rows = []
    for i in range(n):
        # Дата с сезонным весом
        date = np.random.choice(dates_all, p=date_weights)
        cid = np.random.choice(client_ids, p=client_weights)

        client_type = client_type_map[cid]
        manager_id = client_manager_map[cid]

        # Категория с весом (плюс влияние менеджера)
        spec_cat = manager_specialization[manager_id]['cat']
        if spec_cat and np.random.random() < 0.35:
            cat = spec_cat  # менеджер продвигает свою категорию
        else:
            cat = np.random.choice(
                list(cat_weights.keys()),
                p=list(cat_weights.values())
            )

        ci = categories[cat]

        if client_type == 'Опт':
            qty = np.random.randint(*ci['qty_opt'])
            price = np.random.uniform(*ci['price']) * np.random.uniform(0.80, 0.95)
        else:
            qty = np.random.randint(*ci['qty_ret'])
            price = np.random.uniform(*ci['price'])

        total = round(qty * price, 2)

        # Статус из матрицы (тип_клиента, категория)
        probs = status_matrix[(client_type, cat)]
        status = np.random.choice(statuses, p=probs)

        rows.append({
            'Дата': date,
            'Номер_договора': f"Д-2026-{i+1:05d}",
            'ID_клиента': cid,
            'Название_клиента': client_name_map[cid],
            'Тип_клиента': client_type,
            'ID_менеджера': manager_id,
            'ФИО_менеджера': managers[manager_id],
            'Категория': cat,
            'Количество': qty,
            'Цена_за_ед': round(price, 2),
            'Сумма': total,
            'Статус': status
        })

    df = pd.DataFrame(rows).sort_values('Дата').reset_index(drop=True)
    return df


def generate_plans():
    """Генерирует таблицу планов продаж по менеджерам и месяцам"""
    months = pd.date_range('2026-01-01', '2026-06-01', freq='MS')
    # Планы с учётом сезонности (выше в марте и июне)
    seasonal_factor = [0.85, 0.95, 1.15, 1.00, 0.90, 1.20]
    base_plans = {1: 2_500_000, 2: 2_200_000, 3: 2_000_000,
                  4: 1_800_000, 5: 2_100_000}

    rows = []
    for i, month in enumerate(months):
        for mid, base in base_plans.items():
            noise = np.random.uniform(0.95, 1.05)
            plan = int(base * seasonal_factor[i] * noise / 1000) * 1000
            rows.append({
                'ID_менеджера': mid,
                'Месяц': month,
                'Плановая_сумма': plan
            })

    return pd.DataFrame(rows)


def generate_clients(sales_df):
    """Генерирует таблицу клиентов на основе данных продаж"""
    first = sales_df.sort_values('Дата').groupby('ID_клиента').first().reset_index()
    clients = first[['ID_клиента', 'Дата', 'Название_клиента', 'Тип_клиента',
                     'ID_менеджера', 'ФИО_менеджера']].copy()
    clients.columns = ['ID_клиента', 'Дата_первой_сделки', 'Название_клиента',
                       'Тип_клиента', 'ID_менеджера_первой_сделки', 'Менеджер_первой_сделки']

    # Статус: если у клиента >1 сделок за всю историю — Старый, иначе Новый
    deal_counts = sales_df['ID_клиента'].value_counts()
    clients['Статус_клиента'] = clients['ID_клиента'].map(
        lambda x: 'Старый' if deal_counts.get(x, 0) > 1 else 'Новый'
    )

    # Итоги по клиенту: всего сделок, оплачено, отменено, общая сумма
    agg = sales_df.groupby('ID_клиента').agg(
        Всего_сделок=('Номер_договора', 'nunique'),
        Общая_сумма=('Сумма', 'sum'),
        Оплачено=('Сумма', lambda x: sales_df.loc[x.index, 'Статус'].eq('Оплачено').sum()),
        Отменено=('Сумма', lambda x: sales_df.loc[x.index, 'Статус'].eq('Отменено').sum()),
    ).reset_index()
    agg['Оплачено'] = sales_df[sales_df['Статус'] == 'Оплачено'].groupby('ID_клиента').size()
    agg['Отменено'] = sales_df[sales_df['Статус'] == 'Отменено'].groupby('ID_клиента').size()
    agg = agg.fillna(0).astype({'Всего_сделок': int, 'Оплачено': int, 'Отменено': int})

    clients = clients.merge(agg[['ID_клиента', 'Всего_сделок', 'Общая_сумма', 'Оплачено', 'Отменено']],
                            on='ID_клиента', how='left')
    return clients


if __name__ == '__main__':
    sales = generate_sales(2000)
    plans = generate_plans()
    clients = generate_clients(sales)
    sales.to_csv('sales.csv', index=False, encoding='utf-8-sig')
    plans.to_csv('plans.csv', index=False, encoding='utf-8-sig')
    clients.to_csv('clients.csv', index=False, encoding='utf-8-sig')
    print(f'Сгенерировано: {len(sales)} продаж, {len(plans)} планов, {len(clients)} клиентов')
