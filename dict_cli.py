#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CLI для работы со справочниками акта ф. 0510452.

Использование:
    python dict_cli.py list                       # список справочников
    python dict_cli.py show okei                  # весь справочник
    python dict_cli.py find okei "шт"             # поиск подстроки в элементах
    python dict_cli.py get countries --code 643   # элемент по коду
    python dict_cli.py get okonm --name "Мониторы"
    python dict_cli.py fields                     # поля формы -> справочники
    python dict_cli.py validate data.json         # сверить данные fill_act.py
                                                  # со справочниками
"""

import argparse
import json
import sys

from dictionaries import reference as ref


def _print_items(items):
    if not items:
        print("Ничего не найдено.")
        return
    for it in items:
        parts = []
        for k, v in it.items():
            if k in ("note", "group"):
                continue
            parts.append(f"{k}={v}")
        grp = f"[{it['group']}] " if "group" in it else ""
        print(grp + " | ".join(parts))


def cmd_list(_args):
    for name in ref.list_dictionaries():
        data = ref.load(name)
        print(f"{name:12s} {data.get('title', '')}")


def cmd_show(args):
    _print_items([dict(item, group=sec) for sec, item in ref.iter_items(args.name, group=args.group)])


def cmd_find(args):
    _print_items(ref.search(args.name, args.query, group=args.group))


def cmd_get(args):
    item = ref.get_item(args.name, code=args.code, name_=args.text, group=args.group)
    if item is None:
        print("Элемент не найден.", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(item, ensure_ascii=False, indent=2))


def cmd_fields(_args):
    for field, (dic, hint) in ref.fields_for_form().items():
        print(f"{field:28s} <- {dic:28s} {hint}")


def cmd_validate(args):
    """Сверить значения полей данных с кодами/названиями справочников."""
    with open(args.data, encoding="utf-8") as fh:
        data = json.load(fh)

    problems = []

    def check(field_desc, dic, value):
        if not value:
            return
        if ref.get_item(dic, code=str(value)) is None:
            problems.append(f"{field_desc}: значение «{value}» отсутствует в справочнике {dic}")

    check("currency_okoei", "okei", data.get("currency_okoei"))
    check("oktmo", "budgets", data.get("oktmo"))
    check("admin_chapter", "budgets", data.get("admin_chapter"))

    for i, it in enumerate(data.get("items", []), 1):
        check(f"items[{i}].code", "okonm", it.get("code"))
        check(f"items[{i}].country_code", "countries", it.get("country_code"))
        check(f"items[{i}].okei", "okei", it.get("okei"))
        vat = str(it.get("vat_rate", "")).replace("%", "").strip()
        if vat and ref.get_item("vat", code=vat) is None:
            problems.append(f"items[{i}].vat_rate: ставка «{it['vat_rate']}» не из справочника vat")

    pkg = data.get("packaging", {})
    check("packaging.unit_okoei", "okei", pkg.get("unit_okoei"))

    if problems:
        print("Обнаружены расхождения со справочниками:")
        for p in problems:
            print("  -", p)
        sys.exit(1)
    print("Данные соответствуют справочникам.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list").set_defaults(func=cmd_list)

    p = sub.add_parser("show"); p.add_argument("name"); p.add_argument("--group")
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("find"); p.add_argument("name"); p.add_argument("query"); p.add_argument("--group")
    p.set_defaults(func=cmd_find)

    p = sub.add_parser("get"); p.add_argument("name")
    p.add_argument("--code"); p.add_argument("--name", dest="text"); p.add_argument("--group")
    p.set_defaults(func=cmd_get)

    sub.add_parser("fields").set_defaults(func=cmd_fields)

    p = sub.add_parser("validate"); p.add_argument("data")
    p.set_defaults(func=cmd_validate)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
