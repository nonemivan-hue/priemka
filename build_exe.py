#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сборка запускаемого файла (EXE) для инструментов акта ф. 0510452.

Скрипт:
  1. проверяет наличие зависимостей (pyinstaller, openpyxl), при необходимости
     устанавливает их через pip;
  2. собирает два самодостаточных исполняемых файла в папку dist/:
       - fill_act.exe   — заполнение шаблона акта из JSON;
       - dict_cli.exe   — работа со справочниками (list/show/find/get/fields/validate);
  3. копирует справочники dictionaries/json/*.json и sample_data.json рядом
     с собранными EXE (EXE ищут данные в своей папке).

Использование:
    python build_exe.py            # сборка EXE для текущей ОС
    python build_exe.py --clean    # перед сборкой удалить build/, dist/, *.spec
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

TARGETS = [
    {
        "name": "fill_act",
        "script": ROOT / "fill_act.py",
        "hiddenimports": ["openpyxl", "openpyxl.cell._writer"],
    },
    {
        "name": "dict_cli",
        "script": ROOT / "dict_cli.py",
        "hiddenimports": ["dictionaries.reference", "json"],
    },
]


def ensure_module(module: str, pip_name: str | None = None) -> None:
    """Проверяет импорт модуля; при отсутствии ставит пакет через pip."""
    try:
        __import__(module)
        return
    except ImportError:
        pass
    pkg = pip_name or module
    print(f"[setup] Модуль '{module}' не найден — устанавливаю '{pkg}'...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", pkg])


def exe_suffix() -> str:
    return ".exe" if sys.platform == "win32" else ""


def build_target(target: dict) -> Path:
    args = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--console",
        "--name", target["name"],
        "--distpath", str(ROOT / "dist"),
        "--workpath", str(ROOT / "build"),
        "--specpath", str(ROOT / "build"),
    ]
    for hi in target.get("hiddenimports", []):
        args += ["--hidden-import", hi]
    # пакеты справочников нужны для имён модулей (dictionaries.*)
    args += ["--paths", str(ROOT)]
    args.append(str(target["script"]))

    print(f"[build] pyinstaller {' '.join(args[3:])}")
    subprocess.check_call(args)
    out = ROOT / "dist" / (target["name"] + exe_suffix())
    if not out.exists():
        raise SystemExit(f"[error] Ожидался файл {out}, но он не создан.")
    print(f"[ok]    Собран: {out}")
    return out


def copy_runtime_files() -> None:
    """Кладёт рядом с EXE данные, которые программы читают из файловой системы."""
    dist = ROOT / "dist"
    dst_dicts = dist / "dictionaries" / "json"
    src_dicts = ROOT / "dictionaries" / "json"
    if src_dicts.is_dir():
        dst_dicts.mkdir(parents=True, exist_ok=True)
        for f in src_dicts.glob("*.json"):
            shutil.copy2(f, dst_dicts / f.name)
        print(f"[copy]  Справочники -> {dst_dicts} ({len(list(dst_dicts.glob('*.json')))} файлов)")
    sample = ROOT / "sample_data.json"
    if sample.exists():
        shutil.copy2(sample, dist / sample.name)
        print(f"[copy]  {sample.name} -> {dist}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Сборка запусковых EXE-файлов проекта")
    parser.add_argument("--clean", action="store_true",
                        help="удалить build/, dist/ и *.spec перед сборкой")
    args = parser.parse_args()

    if args.clean:
        for p in (ROOT / "build", ROOT / "dist"):
            shutil.rmtree(p, ignore_errors=True)
        for spec in ROOT.glob("*.spec"):
            spec.unlink()
        print("[clean] Удалены build/, dist/, *.spec")

    ensure_module("openpyxl")
    ensure_module("PyInstaller", pip_name="pyinstaller")

    for target in TARGETS:
        build_target(target)

    copy_runtime_files()

    print()
    print("Готово. Запускаемые файлы в dist/:")
    ex = exe_suffix()
    print(f"  dist/fill_act{ex} -i шаблон.XLSX -o акт.xlsx -d data.json")
    print(f"  dist/dict_cli{ex} list | find okei \"шт\" | validate data.json")


if __name__ == "__main__":
    main()
