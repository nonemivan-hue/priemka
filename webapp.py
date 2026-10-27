#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Веб-интерфейс (серверное приложение) для заполнения акта приёмки по форме 0510452.

Перед запуском программа предлагает выбрать IP-адрес и порт для работы:
можно выбрать вариант из предлагаемого списка или ввести свои значения.

Запуск:
    python webapp.py                 # интерактивный выбор IP и порта
    python webapp.py --host 0.0.0.0 --port 8080   # без опроса (для службы/скрипта)
    python webapp.py --yes           # сразу стандартный вариант из списка (без вопросов)

Открыть в браузере:  http://<IP>:<порт>/
"""

import argparse
import io
import ipaddress
import json
import os
import re
import socket
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, jsonify, render_template_string, request, send_file

import fill_act
from dictionaries import reference

app = Flask(__name__)

TEMPLATE_FILE = fill_act.TEMPLATE_FILE

# ---------------------------------------------------------------------------
# Справочник сетевых интерфейсов и список предлагаемых адресов
# ---------------------------------------------------------------------------

def local_interfaces():
    """Список [(имя, ipv4)] всех IPv4-адресов машины."""
    result = []
    try:
        addrs = socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
        seen = set()
        for family, type_, proto, canonname, sa in addrs:
            ip = sa[0]
            if ip not in seen:
                seen.add(ip)
                result.append((canonname or "адаптер", ip))
    except OSError:
        pass
    return result


def suggested_bindings():
    """Готовый список вариантов привязки (host, port, описание)."""
    host_ips = [ip for _, ip in local_interfaces()]
    lan_ip = next((ip for ip in host_ips if not ip.startswith("127.")), None)
    options = [
        ("127.0.0.1", 8080, "только на этом компьютере (localhost)"),
    ]
    if lan_ip:
        options.append((lan_ip, 8080, f"локальная сеть — доступ с других машин ({lan_ip})"))
    options.append(("0.0.0.0", 8080, "все интерфейсы (доступ из любой сети)"))
    return options


def parse_host_port(text):
    """Разбор строки 'IP:порт', 'порт' или 'IP'. Возвращает (host, port) или None."""
    text = text.strip()
    if not text:
        return None
    default_host, default_port = "127.0.0.1", 8080
    if ":" in text and not text.startswith("["):
        host, _, port_s = text.rpartition(":")
        host = host or default_host
        port = int(port_s) if port_s.isdigit() else -1
    elif text.isdigit():                      # ввели только порт
        host, port = default_host, int(text)
    else:                                     # только IP/имя
        host, port = text, default_port
    if host not in ("localhost",):
        try:
            ipaddress.ip_address(host)
        except ValueError:
            if not re.match(r"^[A-Za-z][A-Za-z0-9._-]*$", host):
                return None
    if not (1 <= port <= 65535):
        return None
    return (host, port)


def ask_bind_interactive():
    """Перед запуском предлагает IP и порт: выбрать из списка или ввести свои."""
    print("=" * 62)
    print(" Сервер заполнения акта приёмки (форма 0510452)")
    print("=" * 62)

    options = suggested_bindings()
    print("\nВыберите адрес и порт для запуска сервера:\n")
    for i, (host, port, desc) in enumerate(options, 1):
        print(f"  {i}. {host}:{port:<5}  — {desc}")
    print("  *. свой адрес (введите IP или IP:порт, например 192.168.1.50:9000)")

    host, port = options[0][0], options[0][1]
    while True:
        choice = input("\nВаш выбор [1]: ").strip()
        if choice == "":
            host, port = options[0][0], options[0][1]
            break
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            host, port, _ = options[int(choice) - 1]
            break
        parsed = parse_host_port(choice)
        if parsed:
            host, port = parsed
            break
        print("  Не распознано. Укажите номер варианта или адрес вида IP:порт.")

    # отдельная смена порта, если выбран вариант из списка без порта в явном виде
    new_port = input(f"Порт [{port}] (Enter — оставить): ").strip()
    if new_port:
        if new_port.isdigit() and 1 <= int(new_port) <= 65535:
            port = int(new_port)
        else:
            print("  Некорректный порт, используем", port)

    print(f"\nСервер будет доступен по адресу: http://{host}:{port}/")
    print("(для закрытия — Ctrl+C)\n")
    return host, port


# ---------------------------------------------------------------------------
# HTML-интерфейс
# ---------------------------------------------------------------------------

PAGE = """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Акт приёмки 0510452 — заполнение</title>
<style>
 body{font-family:system-ui,Arial,sans-serif;margin:0;background:#f2f4f7;color:#222}
 header{background:#1f3c88;color:#fff;padding:14px 24px;display:flex;justify-content:space-between;align-items:center}
 header .srv{font-size:13px;opacity:.85}
 main{max-width:1100px;margin:20px auto;padding:0 16px;display:grid;grid-template-columns:1fr 1fr;gap:16px}
 .card{background:#fff;border-radius:10px;box-shadow:0 1px 4px rgba(0,0,0,.1);padding:18px}
 h2{margin-top:0;font-size:16px;color:#1f3c88}
 textarea{width:100%;height:340px;font-family:ui-monospace,Consolas,monospace;font-size:13px;
          border:1px solid #ccd3dd;border-radius:6px;padding:10px;box-sizing:border-box}
 button{background:#1f3c88;color:#fff;border:0;border-radius:6px;padding:10px 18px;font-size:14px;cursor:pointer}
 button:hover{background:#2b52b8}
 .row{display:flex;gap:10px;flex-wrap:wrap;margin-top:12px}
 #msg{margin-top:10px;font-size:14px;white-space:pre-wrap}
 .ok{color:#157347}.err{color:#b02a37}
 .dict{display:flex;gap:8px;margin-bottom:8px}
 select,input[type=text]{border:1px solid #ccd3dd;border-radius:6px;padding:8px;font-size:14px}
 table{border-collapse:collapse;width:100%;font-size:13px}
 th,td{border:1px solid #dde3ec;padding:6px 8px;text-align:left}
 th{background:#eef2f9}
 a.dl{color:#1f3c88;font-weight:600}
</style>
</head>
<body>
<header>
  <div><b>Заполнение акта приёмки товаров, работ, услуг (ОКУД 0510452)</b></div>
  <div class="srv">Сервер: {{ host }}:{{ port }}</div>
</header>
<main>
  <section class="card">
    <h2>Данные документа (JSON)</h2>
    <div class="row">
      <button onclick="loadExample()">Загрузить пример</button>
      <button onclick="validateData()">Проверить</button>
      <button onclick="generate()">Сформировать XLSX ⬇</button>
    </div>
    <textarea id="data" placeholder='{"number": "001", ...}'></textarea>
    <div id="msg"></div>
  </section>

  <section class="card">
    <h2>Справочники</h2>
    <div class="dict">
      <select id="dictName">{% for d in dicts %}<option value="{{ d }}">{{ d }}</option>{% endfor %}</select>
      <input type="text" id="dictQuery" placeholder="поиск по коду или наименованию">
      <button onclick="searchDict()">Найти</button>
    </div>
    <div id="dictResult" style="max-height:420px;overflow:auto"></div>
  </section>
</main>
<script>
const SERVER = "{{ host }}:{{ port }}";
async function loadExample(){
  const r = await fetch('/api/example'); const j = await r.json();
  document.getElementById('data').value = JSON.stringify(j.data, null, 2);
  info('ok', 'Пример загружен — отредактируйте поля и нажмите «Сформировать XLSX».');
}
function info(cls, t){ const m=document.getElementById('msg'); m.className=cls; m.textContent=t; }
async function validateData(){
  let data; try{ data=JSON.parse(document.getElementById('data').value||'{}'); }
  catch(e){ info('err','Ошибка JSON: '+e.message); return; }
  const r = await fetch('/api/validate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  const j = await r.json();
  if(j.ok) info('ok','Данные корректны.');
  else info('err','Замечания:\\n— '+j.errors.join('\\n— '));
}
async function generate(){
  let data; try{ data=JSON.parse(document.getElementById('data').value||'{}'); }
  catch(e){ info('err','Ошибка JSON: '+e.message); return; }
  const r = await fetch('/api/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  if(!r.ok){ const j=await r.json().catch(()=>({error:r.status})); info('err','Не удалось сформировать файл: '+(j.error||r.statusText)); return; }
  const blob = await r.blob();
  const url = URL.createObjectURL(blob);
  const cd = r.headers.get('Content-Disposition')||'';
  const m = cd.match(/filename="?([^\";]+)/);
  const a = document.createElement('a'); a.href=url; a.download=m?m[1]:'act_0510452.xlsx'; a.click();
  URL.revokeObjectURL(url);
  info('ok','Файл сформирован и скачан.');
}
async function searchDict(){
  const name=document.getElementById('dictName').value;
  const q=document.getElementById('dictQuery').value.trim();
  const r=await fetch(`/api/dict/${name}?q=${encodeURIComponent(q)}`);
  const j=await r.json();
  let h='<table><tr><th>Код</th><th>Наименование / значение</th></tr>';
  for(const it of j.items.slice(0,200)) h+=`<tr><td>${it.code??''}</td><td>${it.name??''}</td></tr>`;
  h+='</table>'; if(j.total>j.items.length) h+=`<p>Показаны ${j.items.length} из ${j.total}</p>`;
  document.getElementById('dictResult').innerHTML=h;
}
document.getElementById('dictName').addEventListener('change',searchDict);
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(PAGE, host=RUN["host"], port=RUN["port"],
                                  dicts=reference.list_dictionaries())


@app.route("/api/example")
def api_example():
    return jsonify({"data": fill_act.DATA_EXAMPLE})


@app.route("/api/validate", methods=["POST"])
def api_validate():
    data = request.get_json(force=True, silent=True)
    if data is None:
        return jsonify({"ok": False, "errors": ["тело запроса не является JSON"]})
    errors = []
    check = getattr(reference, "validate_data", None)
    if check:
        errors = list(check(data))
    return jsonify({"ok": not errors, "errors": errors})


@app.route("/api/generate", methods=["POST"])
def api_generate():
    data = request.get_json(force=True, silent=True)
    if data is None:
        return jsonify({"error": "тело запроса не является JSON"}), 400
    try:
        buf = io.BytesIO()
        fill_act.fill_act(template=TEMPLATE_FILE, output=buf, data=data)
        buf.seek(0)
        fname = "act_0510452_%s.xlsx" % str(data.get("number", "draft")).replace("/", "-")
        return send_file(buf, as_attachment=True, download_name=fname,
                         mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/dict/<name>")
def api_dict(name):
    q = request.args.get("q", "").strip()
    try:
        items = reference.search(name, q) if q else list(reference.iter_items(name))[:100]
    except Exception as exc:
        return jsonify({"error": str(exc)}), 404
    total = len(items)
    return jsonify({"items": items[:200], "total": total})


RUN = {"host": "127.0.0.1", "port": 8080}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Веб-сервер заполнения формы 0510452")
    parser.add_argument("--host", help="IP-адрес (если задан — опрос не выполняется)")
    parser.add_argument("--port", type=int, help="порт (если задан — опрос не выполняется)")
    parser.add_argument("--yes", action="store_true", help="без опроса взять первый вариант из списка")
    args = parser.parse_args(argv)

    if args.host and args.port:
        host, port = args.host, args.port
    elif args.yes:
        host, port = suggested_bindings()[0][0], suggested_bindings()[0][1]
    else:
        host, port = ask_bind_interactive()

    RUN.update(host=host, port=port)
    shown = "127.0.0.1" if host == "0.0.0.0" else host
    print(f"Откройте в браузере: http://{shown}:{port}/")
    app.run(host=host, port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
