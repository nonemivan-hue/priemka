# Автоматизация заполнения Акта приемки товаров, работ, услуг (ф. 0510452)

## Установка
Требования: **Python 3.9+** (для сборки EXE — PyInstaller поддерживает 3.8–3.13).

```bash
# 1. (рекомендуется) создать виртуальное окружение
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate

# 2. установить зависимости
pip install -r requirements.txt      # openpyxl (для работы из исходников)

# 3. проверить установку
python dict_cli.py list              # должен вывести список справочников
```

Для сборки запускаемого файла дополнительно нужен `pyinstaller`
(`build_exe.py` установит его автоматически при первом запуске).

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
- `requirements.txt` — зависимости (`pip install -r requirements.txt`)
- `build_exe.py` — сборка запускаемых EXE-файлов (см. ниже)

## Создание запускаемого файла (EXE)
Скрипт `build_exe.py` собирает самодостаточные исполняемые файлы через PyInstaller
(сам устанавливает `pyinstaller`, если его нет) и копирует справочники рядом с ними:

```bash
python build_exe.py            # результат в dist/: fill_act(.exe), dict_cli(.exe)
python build_exe.py --clean    # перед сборкой очистить build/, dist/, *.spec
```

После сборки папка `dist/` переносится на любой компьютер **той же ОС**
(Windows-сборка работает только на Windows; на Linux/macOS запускать бинарники
`fill_act` / `dict_cli` без расширения). Структура для переноса:

```
dist/
├── fill_act.exe              # заполнение акта: fill_act.exe -i шаблон.XLSX -o акт.xlsx -d data.json
├── dict_cli.exe              # справочники: dict_cli.exe list | find okei "шт" | validate data.json
├── sample_data.json          # пример данных
└── dictionaries/json/*.json  # справочники (ищутся в папке рядом с EXE)
```

Проверка собранных файлов:
```bash
dist/dict_cli.exe list
dist/fill_act.exe -i LAW_7445.attach_LAW_497176_1.XLSX -o акт.xlsx -d sample_data.json
```
Примечание: EXE ищут JSON-справочники в своей папке (`dictionaries/json`);
при их отсутствии используйте запуск из исходников (`python fill_act.py ...`).

## Примеры работы со справочниками
```bash
python dict_cli.py list                        # список справочников
python dict_cli.py find okei "шт"              # поиск единиц измерения
python dict_cli.py get countries --code 643    # страна по коду ОКСМ
python dict_cli.py fields                      # поле формы -> справочник
python dict_cli.py validate sample_data.json   # сверка данных со справочниками
```
