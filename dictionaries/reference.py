#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Единый доступ к справочникам для заполнения акта ф. 0510452.

Каждый справочник хранится в dictionaries/json/<name>.json и загружается
лениво (при первом обращении). Модуль предоставляет:

    load(name)                 — сырые данные справочника (dict)
    list_dictionaries()        — список доступных справочников
    search(name, query)        — нечувствительный к регистру поиск по элементам
    get_item(name, code=None, name_=None)  — точное получение элемента
    fields_for_form()          — какие поля данных fill_act.py заполняются
                                 какими справочниками (подсказка форматчику)

Пример:
    from dictionaries import reference as ref
    ref.search("okei", "шт")           -> единицы измерения со «шт»
    ref.get_item("countries", code="643") -> {"code": "643", "name": "Россия", ...}
"""

import json
import os
import re
import unicodedata

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_DIR = os.path.join(BASE_DIR, "json")

# Совместимость: словари могут лежать и в dictionaries/data (устаревший вариант)
if not os.path.isdir(JSON_DIR):
    JSON_DIR = os.path.join(BASE_DIR, "data")

_CACHE = {}

#: имя справочника -> ключ списка элементов внутри JSON (None = весь dict)
LIST_KEYS = {
    "okonm": "items",
    "okei": "items",
    "countries": "items",
    "budgets": None,      # несколько списков: budgets / grbs / oktmo
    "docs": None,         # несколько списков по видам документов
    "roles": None,        # несколько списков по блокам подписей
    "vat": "vat_rates",
}


def list_dictionaries():
    """Имена всех справочников, для которых есть JSON-файл."""
    return sorted(
        os.path.splitext(f)[0]
        for f in os.listdir(JSON_DIR)
        if f.endswith(".json")
    )


def load(name):
    """Загрузить (с кэшированием) JSON-данные справочника `name`."""
    if name not in _CACHE:
        path = os.path.join(JSON_DIR, f"{name}.json")
        if not os.path.exists(path):
            raise KeyError(
                f"Справочник «{name}» не найден. "
                f"Доступны: {', '.join(list_dictionaries())}"
            )
        with open(path, encoding="utf-8") as fh:
            _CACHE[name] = json.load(fh)
    return _CACHE[name]


def iter_items(name, group=None):
    """Итерировать элементы справочника.

    Для справочников с несколькими группами (budgets, docs, roles) можно
    указать group — имя внутренней секции; иначе обходятся все секции-списки.
    """
    data = load(name)
    key = LIST_KEYS.get(name)
    if key:
        for it in data.get(key, []):
            yield (key, it)
        return
    # многосекционные справочники
    for sec, val in data.items():
        if isinstance(val, list) and all(isinstance(x, dict) for x in val):
            if group and sec != group:
                continue
            for it in val:
                yield (sec, it)


def _norm(s):
    s = unicodedata.normalize("NFKC", str(s)).lower().strip()
    # ё -> е, схлопываем пробелы/неbreakable
    return re.sub(r"\s+", " ", s.replace("ё", "е"))


def search(name, query, group=None):
    """Найти элементы, у которых любое текстовое/числовое поле содержит query."""
    q = _norm(query)
    out = []
    for sec, item in iter_items(name, group=group):
        haystack = _norm(" ".join(str(v) for v in item.values()))
        if q in haystack:
            out.append({"group": sec, **item})
    return out


def get_item(name, code=None, name_=None, group=None):
    """Точное получение элемента по коду или наименованию (нечувт. к регистру).

    Код ищется в полях «code» или «chapter» (главы по БК).
    """
    for _, item in iter_items(name, group=group):
        if code is not None and _norm(item.get("code", item.get("chapter"))) == _norm(code):
            return item
        if name_ is not None and _norm(item.get("name")) == _norm(name_):
            return item
    return None


# ---------------------------------------------------------------------------
# Подсказка: какой справочник закрывает какие поля данных fill_act.py
# ---------------------------------------------------------------------------
FORM_FIELDS = {
    "currency_okoei": ("okei", "код ОКЕИ валюты (строка 18 листа «стр.1», колонка КОДЫ)"),
    "currency_name": ("okei", "наименование валюты (строка 18)"),
    "budget_name": ("budgets:budgets", "наименование бюджета (строка 17)"),
    "admin_chapter": ("budgets:grbs", "глава по БК / ГРБС (строка 16, колонка КОДЫ)"),
    "oktmo": ("budgets:oktmo", "код ОКТМО (строка 17, колонка КОДЫ)"),
    "accept_basis_text": ("docs:basis_documents", "документ-основание приемки (строки 31–33)"),
    "commission_doc_text": ("docs:commission_documents", "документ о создании комиссии (строки 29–30)"),
    "shipment_doc_text": ("docs:shipment_documents", "документ об отгрузке (строки 36–37)"),
    "payment_doc_text": ("docs:payment_documents", "платежно-расчетный документ (строка 20)"),
    "attachments[].name": ("docs:attachments", "перечень приложений (лист «стр.2_3»)"),
    "items[].code": ("okonm", "код товара/работы ОКПД2 (таблица 4, графа «Код»)"),
    "items[].country_code": ("countries", "цифровой код страны происхождения"),
    "items[].country_name": ("countries", "наименование страны происхождения"),
    "items[].okei": ("okei", "код единицы измерения по ОКЕИ"),
    "items[].okei_cond": ("okei", "условное обозначение единицы измерения"),
    "items[].vat_rate": ("vat", "ставка НДС (0 / 10% / 20%)"),
    "packaging.unit_okoei": ("okei", "код ОКЕИ единицы места (таблица 3)"),
    "approved_head.position": ("roles:approve", "должность утверждающего (шапка)"),
    "accepted_head.position": ("roles:accepted_obligation", "должность принявшего обязательство"),
    "chairman.position": ("roles:commission", "председатель комиссии"),
    "members[].position": ("roles:commission", "члены комиссии"),
    "supplier_rep.position": ("roles:acceptance_participants", "представитель поставщика"),
    "accepted_by.position": ("roles:acceptance_participants", "товары принял"),
}


def fields_for_form():
    return FORM_FIELDS
