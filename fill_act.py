#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Программа заполнения Акта приемки товаров, работ, услуг (ф. 0510452).

Файл-шаблон: LAW_7445.attach_LAW_497176_1.XLSX (листы «стр.1» и «стр.2_3»).

Использование:
    python fill_act.py                     # заполнить примером из DATA_EXAMPLE
    python fill_act.py -d data.json        # заполнить из JSON-файла данных
    python fill_act.py -i act.xlsx -o out.xlsx -d data.json

Структура JSON с данными — см. словарь DATA_EXAMPLE ниже.
Все поля необязательные: незаполненные ячейки остаются как в шаблоне.
"""

import argparse
import json
import sys
from datetime import date, datetime

import openpyxl

TEMPLATE_FILE = "LAW_7445.attach_LAW_497176_1.XLSX"


def lookup(dic, code=None, name_=None, group=None):
    """Опциональная сверка значения со справочником (dictionaries/reference.py).

    Возвращает найденный элемент или None (справочники не обязательны для
    заполнения — это подсказки форматчику).
    """
    try:
        from dictionaries import reference as ref
    except ImportError:
        return None
    return ref.get_item(dic, code=code, name_=name_, group=group)

# ---------------------------------------------------------------------------
# Пример данных для заполнения (можно заменить своим JSON-файлом через -d)
# ---------------------------------------------------------------------------
DATA_EXAMPLE = {
    "act_number": "1",
    "date_accept": {"dd": "28", "mm": "10", "yyyy": "2026"},          # дата акта
    "amount_words": "Двести тридцать тысяч рублей 00 копеек",          # сумма прописью
    "approved_head": {                                                 # блок «УТВЕРЖДАЮ»
        "position": "Директор",
        "signature": "",
        "fio": "Иванов И.И.",
        "date": {"dd": "28", "mm": "10", "yyyy": "2026"},
    },
    "accepted_head": {                                                 # блок «ПРИНЯТО ДЕНЕЖНОЕ ОБЯЗАТЕЛЬСТВО»
        "position": "Главный бухгалтер",
        "signature": "",
        "fio": "Петрова А.С.",
        "date": {"dd": "28", "mm": "10", "yyyy": "2026"},
    },
    "institution": "Государственное бюджетное учреждение города Москвы «Пример»",
    "branch": "",
    "subdivision": "Отдел материально-технического обеспечения",
    "admin_name": "Департамент здравоохранения города Москвы",
    "admin_chapter": "0900",                                           # Глава по БК
    "budget_name": "Бюджет города Москвы",
    "currency_name": "Российский рубль",
    "currency_okoei": "643",
    "recipient_address": "123456, г. Москва, ул. Примерная, д. 1",
    "payment_doc_number": "12345",
    "payment_doc_date": "15.10.2026",
    "customer_full": "ГБУЗ «Пример»",
    "customer_ogrn": "1027700000001",
    "customer_inn": "7700000001",
    "customer_kpp": "770001001",
    "customer_ls": "01770000000",
    "customer_section": "1",
    "supplier_ls": "",
    "supplier_section": "",
    "oktmo": "45329000",
    "svod_reestr_receiver": "0010900001",
    "payment_doc_text": "Соглашение о поставке от 01.10.2026 № 12-П",
    "commission_doc_text": "Приказ по учреждению о создании приемочной комиссии",
    "accept_basis_text": "Государственный контракт от 05.10.2026 № 01772000012-26",
    "shipment_doc_text": "Товарная накладная",
    "customer_address": "123456, г. Москва, ул. Примерная, д. 1",
    "delivery_place": "Склад получателя: г. Москва, ул. Складская, д. 2",
    "commission_doc_number": "45-к",
    "commission_doc_date": "01.10.2026",
    "accept_basis_number": "КС-2",
    "accept_basis_date": "27.10.2026",
    "igk": "221134567890123456789012345678901234",                     # ИГК контракта
    "shipment_doc_number": "НК-000123",
    "shipment_doc_date": "25.10.2026",
    "other_doc_number": "",
    "other_doc_date": "",
    # Таблица 1: поставщик / грузоотправитель / страхователь
    "suppliers": {
        "supplier": ["ООО «Ромашка»", "ООО «Ромашка»",
                     "111111, г. Москва, ул. Поставщиков, д. 5",
                     "1027700000002", "7701000001", "770101001", "", ""],
        "shipper":  ["ООО «Логистик»", "ООО «Логистик»",
                     "122222, г. Москва, ул. Логистическая, д. 3",
                     "1037700000003", "7702000002", "770202001", "", ""],
        "insurer":  ["", "", "", "", "", "", "", ""],
    },
    # Лист стр.2_3 — таблица 2 (транспортировка), строка 8
    "transport": {
        "send_date": "24.10.2026", "send_time": "09:00",
        "arrive_date": "25.10.2026", "arrive_time": "18:30",
        "issue_date": "25.10.2026", "issue_time": "19:00",
        "open_date": "26.10.2026", "open_time": "08:30",
        "deliver_date": "26.10.2026", "deliver_time": "09:00",
        "accept_start": "09:15", "accept_end": "10:45",
        "place": "г. Москва, ул. Складская, д. 2",
    },
    # Таблица 3 (пломбы/упаковка), строка 15
    "packaging": {
        "seals": "Пломбы целы", "package_type": "Гофрокороб",
        "package_state": "Не повреждена", "unit_name": "штука", "unit_okoei": "796",
        "measure_method": "Счет мест", "places": "10",
        "mass_from": "1,2", "mass_to": "1,2",
        "marked_goods": "Монитор 24\"", "storage": "Сухой отапливаемый склад",
    },
    # Подписи на стр.2 (до таблицы 4)
    "supplier_rep_pre": {
        "position": "Менеджер", "fio": "Сидоров В.В.",
        "date": {"dd": "28", "mm": "10", "yyyy": "2026"},
    },
    "accepted_by_pre": {
        "position": "Заведующий складом", "fio": "Кузнецова М.П.",
        "date": {"dd": "28", "mm": "10", "yyyy": "2026"},
    },
    # Таблица 4: сведения о приемке (строки 33, 34; итого — строка 35)
    "items": [
        {
            "code": "32.50.50.190", "name": "Монитор 24 дюйма",
            "country_code": "643", "country_name": "Россия",
            "okei": "796", "okei_cond": "шт",
            "qty_doc": 10, "price": 15000, "no_vat": 150000,
            "vat_rate": "20%", "vat": 30000, "with_vat": 180000,
            "decl": "", "cert": "", "fact_qty": 10, "fact_bad": "",
        },
        {
            "code": "32.50.50.190", "name": "Клавиатура USB",
            "country_code": "156", "country_name": "Китай",
            "okei": "796", "okei_cond": "шт",
            "qty_doc": 10, "price": 5000, "no_vat": 50000,
            "vat_rate": "20%", "vat": 10000, "with_vat": 60000,
            "decl": "1000000/251026/0000001", "cert": "ТС № RU C-RU.АЕ87.Б.00123",
            "fact_qty": 10, "fact_bad": "",
        },
    ],
    # Таблица 5: расхождения (строки 43, 44; итого — строка 45)
    "discrepancies": [
        {
            "code": "", "name": "",
            "total_qty": 1, "total_sum": 5000,
            "short_qty": 1, "short_sum": 5000,
            "extra_qty": "", "extra_sum": "",
            "defect_qty": "", "defect_sum": "",
            "country_code": "", "country_name": "",
            "decl": "", "specs": "", "other": "",
        },
    ],
    # Раздел 6 — строительно-монтажные работы (заполняется только если smr_present=true)
    "smr_present": False,
    "smr": {
        "period_from": "01.09.2026", "period_to": "28.10.2026",
        "construction": "Стройка-1", "object": "Объект: капремонт кровли",
        "object_uid": "77-1-2345678901",
        "works": [],       # строки 58, 59
        "costs": [],       # строки 67, 68 раздела 6.2
        "costs_total": "", "costs_vat": "", "costs_with_vat": "",
    },
    # Приложения (строки 74/76)
    "attachments": [
        {"number": "1", "name": "Товарная накладная НК-000123", "file": "nk_000123.pdf"},
        {"number": "2", "name": "Универсальный передаточный документ", "file": "upd_000123.pdf"},
    ],
    # Итоговые подписи
    "chairman": {"position": "Начальник отдела", "fio": "Смирнов Д.А."},
    "members": [
        {"position": "Ст. бухгалтер", "fio": "Орлова Е.Н."},
        {"position": "Юрист", "fio": "Морозов П.П."},
        {"position": "Зав. складом", "fio": "Кузнецова М.П."},
    ],
    "executor": {
        "position": "Юрист", "fio": "Морозов П.П.",
        "phone": "+7(495)123-45-67", "email": "example@mail.ru",
    },
    "supplier_rep": {
        "position": "Менеджер", "fio": "Сидоров В.В.",
        "date": {"dd": "28", "mm": "10", "yyyy": "2026"},
    },
    "accepted_by": {
        "position": "Заведующий складом", "fio": "Кузнецова М.П.",
        "date": {"dd": "28", "mm": "10", "yyyy": "2026"},
    },
    "customer_rep": {
        "position": "Начальник хозотдела", "fio": "Федоров И.И.",
        "date": {"dd": "28", "mm": "10", "yyyy": "2026"},
    },
    "build_control_rep": {
        "position": "", "fio": "", "date": None,
    },
}


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def set_cell(ws, anchor, value):
    """Записать значение в ячейку; если это часть объединённого диапазона —
    записать в его верхнюю левую (головную) ячейку."""
    if value is None or value == "":
        return
    cell = ws[anchor]
    for mr in ws.merged_cells.ranges:
        if cell.coordinate in mr:
            cell = ws.cell(mr.min_row, mr.min_col)
            break
    cell.value = value


def split_date(d):
    """Разбить дату (строка 'ДД.ММ.ГГГГ', date/datetime или dict) на части."""
    if not d:
        return None
    if isinstance(d, dict):
        return d
    if isinstance(d, (date, datetime)):
        return {"dd": f"{d.day:02d}", "mm": f"{d.month:02d}", "yyyy": str(d.year)}
    parts = str(d).split(".")
    if len(parts) == 3:
        return {"dd": parts[0], "mm": parts[1], "yyyy": parts[2]}
    raise ValueError(f"Не удалось распознать дату: {d!r}")


def fill_date_block(ws, day_anchor, month_anchor, year_anchor, d):
    """Заполнить блок «\"__\" __________ 20__ г.». d — строка/дата/dict."""
    dd_mm_yyyy = split_date(d.get("date") if isinstance(d, dict) and "date" in d else d)
    if not dd_mm_yyyy:
        return
    set_cell(ws, day_anchor, dd_mm_yyyy["dd"])
    set_cell(ws, month_anchor, dd_mm_yyyy["mm"])
    set_cell(ws, year_anchor, dd_mm_yyyy["yyyy"])


def fill_signature(ws, pos_anchor, sign_anchor, fio_anchor, block):
    if not block:
        return
    set_cell(ws, pos_anchor, block.get("position"))
    set_cell(ws, sign_anchor, block.get("signature"))
    set_cell(ws, fio_anchor, block.get("fio"))


# ---------------------------------------------------------------------------
# Заполнение листа «стр.1»
# ---------------------------------------------------------------------------

def fill_sheet1(wb, data):
    ws = wb["стр.1"]

    # Шапка: сумма принятого денежного обязательства
    set_cell(ws, "H3", data.get("amount_words"))

    # Блок «ПРИНЯТО ДЕНЕЖНОЕ ОБЯЗАТЕЛЬСТВО» (слева)
    fill_signature(ws, "A5", "AA5", "AQ5", data.get("accepted_head"))
    fill_date_block(ws, "C7", "H7", "W7", data.get("accepted_head") or data.get("date_accept"))

    # Блок «УТВЕРЖДАЮ» (справа)
    fill_signature(ws, "CQ5", "DQ5", "EG5", data.get("approved_head"))
    fill_date_block(ws, "CR7", "CW7", "DL7", data.get("approved_head") or data.get("date_accept"))

    # Номер и дата акта
    set_cell(ws, "CI9", data.get("act_number"))
    d = split_date(data.get("date_accept"))
    if d:
        set_cell(ws, "BW12", d["dd"])
        set_cell(ws, "CB12", d["mm"])
        set_cell(ws, "CQ12", d["yyyy"])

    # Строки 13–20: реквизиты учреждения (текст) + коды (колонка ER)
    set_cell(ws, "AS13", data.get("institution"))            # Учреждение (получатель)
    set_cell(ws, "AS14", data.get("branch"))                 # Обособленное подразделение
    set_cell(ws, "AS15", data.get("subdivision"))            # Структурное подразделение
    set_cell(ws, "AS16", data.get("admin_name"))             # Главный администратор (Учредитель)
    set_cell(ws, "AS17", data.get("budget_name"))            # Наименование бюджета
    set_cell(ws, "AS18", data.get("currency_name"))          # Валюта (наименование)
    set_cell(ws, "AS19", data.get("recipient_address"))      # Адрес грузополучателя
    set_cell(ws, "AS20", data.get("payment_doc_text"))       # Реквизиты платежно-расчетного документа
    # значения кодов из правого столбца «КОДЫ»
    set_cell(ws, "ER13", data.get("svod_reestr_receiver"))   # по Сводному реестру (получатель)
    set_cell(ws, "ER14", data.get("svod_reestr_branch"))     # по Сводному реестру (обособленное)
    set_cell(ws, "ER16", data.get("admin_chapter"))           # Глава по БК
    set_cell(ws, "ER17", data.get("oktmo"))                   # по ОКТМО
    set_cell(ws, "ER18", data.get("currency_okoei"))          # по ОКЕИ
    set_cell(ws, "ER20", data.get("payment_doc_number"))      # Номер
    set_cell(ws, "ER21", data.get("payment_doc_date"))        # Дата

    # Заказчик (строки 21–28)
    set_cell(ws, "AS21", data.get("customer_full"))          # наименование заказчика (AS21:EB22)
    set_cell(ws, "ER22", data.get("customer_ogrn"))          # ОГРН (ER22:FE23)
    set_cell(ws, "DP24", data.get("customer_inn"))           # ИНН
    set_cell(ws, "ER24", data.get("customer_kpp"))           # КПП
    set_cell(ws, "CQ25", data.get("customer_ls"))            # Лицевой счет (заказчика)
    set_cell(ws, "ER25", data.get("supplier_ls"))            # Лицевой счет (поставщика)
    set_cell(ws, "EQ26", data.get("customer_section"))       # Раздел ЛС (заказчика)
    set_cell(ws, "ER26", data.get("supplier_section"))       # Раздел ЛС (поставщика)
    set_cell(ws, "AS27", data.get("customer_address"))
    set_cell(ws, "AS28", data.get("delivery_place"))

    # Документ-основание о создании комиссии (29–30)
    set_cell(ws, "AS29", data.get("commission_doc_text"))
    set_cell(ws, "ER29", data.get("commission_doc_number"))  # Номер
    set_cell(ws, "ER30", data.get("commission_doc_date"))    # Дата

    # Основание приемки (31–33) + ИГК
    set_cell(ws, "AS31", data.get("accept_basis_text"))
    set_cell(ws, "ER31", data.get("accept_basis_number"))    # Номер
    set_cell(ws, "DB33", data.get("igk"))                    # ИГК контракта
    set_cell(ws, "ER33", data.get("accept_basis_date"))      # Дата

    # Документ об отгрузке (36–37) и другой документ (38–39)
    set_cell(ws, "AS36", data.get("shipment_doc_text"))
    set_cell(ws, "ER36", data.get("shipment_doc_number"))
    set_cell(ws, "ER37", data.get("shipment_doc_date"))
    set_cell(ws, "ER38", data.get("other_doc_number"))
    set_cell(ws, "ER39", data.get("other_doc_date"))

    # Таблица 1: поставщик / грузоотправитель / страхователь (строки 44–51)
    sup = data.get("suppliers", {})
    anchors = {
        "supplier":    ("CA", "DA"),
        "shipper":     ("DB", "EB"),
        "insurer":     ("EC", "FE"),
    }
    for key, (col_a, col_b) in anchors.items():
        values = sup.get(key) or []
        for i, row in enumerate(range(44, 52)):
            if i < len(values):
                set_cell(ws, f"{col_a}{row}", values[i])


# ---------------------------------------------------------------------------
# Заполнение листа «стр.2_3»
# ---------------------------------------------------------------------------

def fill_sheet23(wb, data):
    ws = wb["стр.2_3"]

    # Таблица 2 — транспортировка (строка 8)
    t = data.get("transport")
    if t:
        set_cell(ws, "G8", t.get("send_date"))
        set_cell(ws, "S8", t.get("send_time"))
        set_cell(ws, "AC8", t.get("arrive_date"))
        set_cell(ws, "AO8", t.get("arrive_time"))
        set_cell(ws, "AY8", t.get("issue_date"))
        set_cell(ws, "BK8", t.get("issue_time"))
        set_cell(ws, "BU8", t.get("open_date"))
        set_cell(ws, "CG8", t.get("open_time"))
        set_cell(ws, "CQ8", t.get("deliver_date"))
        set_cell(ws, "DC8", t.get("deliver_time"))
        set_cell(ws, "DM8", t.get("accept_start"))
        set_cell(ws, "DY8", t.get("accept_end"))
        set_cell(ws, "EK8", t.get("place"))

    # Таблица 3 — пломбы/упаковка (строка 15)
    p = data.get("packaging")
    if p:
        set_cell(ws, "G15", p.get("seals"))
        set_cell(ws, "R15", p.get("package_type"))
        set_cell(ws, "AC15", p.get("package_state"))
        set_cell(ws, "AO15", p.get("unit_name"))
        set_cell(ws, "BB15", p.get("unit_okoei"))
        set_cell(ws, "BL15", p.get("measure_method"))
        set_cell(ws, "BZ15", p.get("places"))
        set_cell(ws, "CL15", p.get("mass_from"))
        set_cell(ws, "CV15", p.get("mass_to"))
        set_cell(ws, "DF15", p.get("marked_goods"))
        set_cell(ws, "EN15", p.get("storage"))

    # Подписи до таблицы 4 (строки 17–25)
    sp = data.get("supplier_rep_pre")
    if sp:
        set_cell(ws, "AD17", sp.get("position"))
        set_cell(ws, "BE17", sp.get("signature"))
        set_cell(ws, "BV17", sp.get("fio"))
        fill_date_block(ws, "C20", "H20", "R20", sp)
    ab = data.get("accepted_by_pre")
    if ab:
        set_cell(ws, "AD22", ab.get("position"))
        set_cell(ws, "BE22", ab.get("signature"))
        set_cell(ws, "BV22", ab.get("fio"))
        fill_date_block(ws, "C25", "H25", "R25", ab)

    # Таблица 4 — сведения о приемке (строки 33–34, итого 35)
    item_cols = ["F", "O", "AH", "AO", "AX", "BD", "BL", "BT", "CC",
                 "CL", "CT", "DD", "DN", "DZ", "EI", "EP", "EX"]
    item_keys = ["code", "name", "country_code", "country_name", "okei",
                 "okei_cond", "qty_doc", "price", "no_vat", "vat_rate",
                 "vat", "with_vat", "decl", "cert", "fact_qty", "fact_bad", None]
    first_data_row = 33
    max_items = 2
    items = (data.get("items") or [])[:max_items]
    for idx, it in enumerate(items):
        r = first_data_row + idx
        for col, key in zip(item_cols, item_keys):
            if key:
                set_cell(ws, f"{col}{r}", it.get(key))
    # Итого (строка 35)
    def sum_col(key):
        vals = [it.get(key) for it in items if isinstance(it.get(key), (int, float))]
        return sum(vals) if vals else None
    set_cell(ws, "CC35", sum_col("no_vat"))
    set_cell(ws, "CT35", sum_col("vat"))
    set_cell(ws, "DD35", sum_col("with_vat"))

    # Таблица 5 — расхождения (строки 43–44, итого 45)
    disc_cols = ["F", "O", "AL", "AT", "BD", "BL", "BV", "CD", "CN",
                 "CV", "DF", "DM", "DV", "EL", "EW"]
    disc_keys = ["code", "name", "total_qty", "total_sum", "short_qty",
                 "short_sum", "extra_qty", "extra_sum", "defect_qty",
                 "defect_sum", "country_code", "country_name", "decl",
                 "specs", "other"]
    discs = (data.get("discrepancies") or [])[:2]
    for idx, it in enumerate(discs):
        r = 43 + idx
        for col, key in zip(disc_cols, disc_keys):
            set_cell(ws, f"{col}{r}", it.get(key))
    def dsum(key):
        vals = [it.get(key) for it in discs if isinstance(it.get(key), (int, float))]
        return sum(vals) if vals else None
    set_cell(ws, "AL45", dsum("total_qty"))
    set_cell(ws, "AT45", dsum("total_sum"))
    set_cell(ws, "BD45", dsum("short_qty"))
    set_cell(ws, "BL45", dsum("short_sum"))
    set_cell(ws, "BV45", dsum("extra_qty"))
    set_cell(ws, "CD45", dsum("extra_sum"))
    set_cell(ws, "CN45", dsum("defect_qty"))
    set_cell(ws, "CV45", dsum("defect_sum"))

    # Раздел 6 — СМР (заполняется при smr_present)
    if data.get("smr_present"):
        s = data.get("smr", {})
        set_cell(ws, "EB51", s.get("period_from"))
        set_cell(ws, "EQ51", s.get("period_to"))
        set_cell(ws, "L52", s.get("construction"))
        set_cell(ws, "L53", s.get("object"))
        set_cell(ws, "EQ53", s.get("object_uid"))
        work_cols = ["A", "K", "W", "BA", "BV", "CJ", "CY", "DQ", "EI"]
        work_keys = ["num", "est_num", "name", "rate_num", "okei",
                     "okei_cond", "qty", "price", "cost"]
        for idx, w in enumerate((s.get("works") or [])[:2]):
            r = 58 + idx
            for col, key in zip(work_cols, work_keys):
                set_cell(ws, f"{col}{r}", w.get(key))
        cost_cols = ["A", "I", "BV", "CF", "DF", "EF"]
        cost_keys = ["num", "name", "code", "since_start", "since_year", "period"]
        for idx, c in enumerate((s.get("costs") or [])[:2]):
            r = 67 + idx
            for col, key in zip(cost_cols, cost_keys):
                set_cell(ws, f"{col}{r}", c.get(key))
        set_cell(ws, "CF69", s.get("costs_total"))
        set_cell(ws, "CF70", s.get("costs_vat"))
        set_cell(ws, "CF71", s.get("costs_with_vat"))

    # Приложения (строки 74, 76)
    att_rows = [(74, "P74", "AA74", "CW74"), (76, "P76", "AA76", "CW76")]
    for i, att in enumerate((data.get("attachments") or [])[:2]):
        _, num_a, name_a, file_a = att_rows[i]
        set_cell(ws, num_a, att.get("number"))
        set_cell(ws, name_a, att.get("name"))
        set_cell(ws, file_a, att.get("file"))

    # Подписи председателя/членов комиссии (строки 78–85)
    ch = data.get("chairman")
    if ch:
        set_cell(ws, "AB78", ch.get("position"))
        set_cell(ws, "AY78", ch.get("signature"))
        set_cell(ws, "BQ78", ch.get("fio"))
    for i, m in enumerate((data.get("members") or [])[:3]):
        base = 80 + i * 2
        set_cell(ws, f"AB{base}", m.get("position"))
        set_cell(ws, f"AY{base}", m.get("signature"))
        set_cell(ws, f"BQ{base}", m.get("fio"))

    ex = data.get("executor")
    if ex:
        set_cell(ws, "AB86", ex.get("position"))
        set_cell(ws, "AY86", ex.get("signature"))
        set_cell(ws, "BQ86", ex.get("fio"))
        set_cell(ws, "CP86", ex.get("phone"))
        set_cell(ws, "DM86", ex.get("email"))

    sr = data.get("supplier_rep")
    if sr:
        set_cell(ws, "AB88", sr.get("position"))
        set_cell(ws, "AY88", sr.get("signature"))
        set_cell(ws, "BQ88", sr.get("fio"))
        fill_date_block(ws, "C91", "H91", "R91", sr)

    ac = data.get("accepted_by")
    if ac:
        set_cell(ws, "AB93", ac.get("position"))
        set_cell(ws, "AY93", ac.get("signature"))
        set_cell(ws, "BQ93", ac.get("fio"))
        fill_date_block(ws, "C96", "H96", "R96", ac)

    cr = data.get("customer_rep")
    if cr:
        set_cell(ws, "AB98", cr.get("position"))
        set_cell(ws, "AY98", cr.get("signature"))
        set_cell(ws, "BQ98", cr.get("fio"))
        fill_date_block(ws, "C101", "H101", "R101", cr)

    bc = data.get("build_control_rep")
    if bc:
        set_cell(ws, "AB103", bc.get("position"))
        set_cell(ws, "AY103", bc.get("signature"))
        set_cell(ws, "BQ103", bc.get("fio"))
        fill_date_block(ws, "C106", "H106", "R106", bc)


# ---------------------------------------------------------------------------
# Основная функция
# ---------------------------------------------------------------------------

def fill_act(template=TEMPLATE_FILE, output=None, data=None):
    data = data if data is not None else DATA_EXAMPLE
    wb = openpyxl.load_workbook(template)
    fill_sheet1(wb, data)
    fill_sheet23(wb, data)
    output = output or template
    wb.save(output)
    print(f"Файл заполнен и сохранён: {output}")
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Заполнение Акта приемки товаров, работ, услуг (ф. 0510452)")
    parser.add_argument("-i", "--input", default=TEMPLATE_FILE,
                        help="путь к файлу-шаблону XLSX")
    parser.add_argument("-o", "--output", default=None,
                        help="путь для результата (по умолчанию — перезаписать входной файл)")
    parser.add_argument("-d", "--data", default=None,
                        help="JSON-файл с данными (по умолчанию — встроенный пример)")
    args = parser.parse_args(argv)

    data = DATA_EXAMPLE
    if args.data:
        with open(args.data, encoding="utf-8") as f:
            data = json.load(f)

    fill_act(template=args.input, output=args.output, data=data)


if __name__ == "__main__":
    main()
