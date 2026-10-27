# Автоматизация заполнения Акта приемки товаров, работ, услуг (ф. 0510452)

## Состав
- `LAW_7445.attach_LAW_497176_1.XLSX` — шаблон формы (листы «стр.1», «стр.2_3»)
- `fill_act.py` — программа заполнения из JSON (`python fill_act.py -d data.json`)
- `sample_data.json` — пример данных (совместим с `-d`)
- `filled_act.xlsx` — демонстрационный заполненный акт
- `dictionaries/` — справочники для подготовки данных:
  - `json/*.json` — данные: ОКПД2 (`okonm`), ОКЕИ (`okei`), страны (`countries`),
    бюджеты/ГРБС/ОКТМО (`budgets`), документы (`docs`), должности (`roles`), НДС (`vat`)
  - `reference.py` — API: load/search/get_item/fields_for_form
  - `dict_cli.py` (в корне) — CLI: list/show/find/get/fields/validate

## Примеры работы со справочниками
```bash
python dict_cli.py list                        # список справочников
python dict_cli.py find okei "шт"              # поиск единиц измерения
python dict_cli.py get countries --code 643    # страна по коду ОКСМ
python dict_cli.py fields                      # поле формы -> справочник
python dict_cli.py validate sample_data.json   # сверка данных со справочниками
```
