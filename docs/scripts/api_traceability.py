# Простежуваність REQ-ID ↔ API operations (ЛР №4).
#
# Читає api/openapi.yaml (x-req-ids, x-side-effects, x-acceptance-criteria,
# x-roles), сценарії з tests/contract/run-scenarios.ps1 і критерії з
# spec/srs.md. Пише:
#   docs/api-traceability.md   — таблиця операцій і покриття вимог;
#   spec/traceability.csv      — колонка «API» після «Тікет» (створюється,
#                                якщо її немає; інші колонки, BOM і кінці
#                                рядків не змінюються).
# Запуск із кореня репозиторію:  python docs/scripts/api_traceability.py .
# Потрібен PyYAML:               python -m pip install pyyaml
import re
import sys
from collections import defaultdict

import yaml

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
SPEC = f"{ROOT}/api/openapi.yaml"
SCEN = f"{ROOT}/tests/contract/run-scenarios.ps1"
SRS = f"{ROOT}/spec/srs.md"
TRACE = f"{ROOT}/spec/traceability.csv"
OUT = f"{ROOT}/docs/api-traceability.md"

METHODS = ("get", "post", "put", "patch", "delete")
AUTOMATIC_NOTE = ("Автоматична дія системи, операції немає: результат видно "
                  "через getBooking і listBookings.")


def fr_key(r):
    m = re.match(r"(N?FR)-(\d+)", r)
    return (m.group(1) != "FR", int(m.group(2))) if m else (2, r)


# --- Операції -----------------------------------------------------------
spec = yaml.safe_load(open(SPEC, encoding="utf-8"))
ops = []
for path, item in spec["paths"].items():
    for method in METHODS:
        op = item.get(method)
        if not op:
            continue
        ops.append({
            "id": op["operationId"],
            "method": method.upper(),
            "path": path,
            "req": op.get("x-req-ids", []),
            "side": op.get("x-side-effects", []),
            "ac": op.get("x-acceptance-criteria", []),
            "roles": op.get("x-roles", []),
            "rx": re.compile("^" + re.sub(r"\{[^}]+\}", "[^/]+", path) + "$"),
        })

# --- Сценарії -----------------------------------------------------------
scen_by_op = defaultdict(list)
scen_ac = set()
scen_line = re.compile(r"Id='([A-Z]-\d+)';\s*Req='([^']*)'.*?M='(\w+)';\s*P=['\"]([^'\"]+)['\"]")
for line in open(SCEN, encoding="utf-8-sig"):
    m = scen_line.search(line)
    if not m:
        continue
    sid, req, method, p = m.groups()
    p = re.sub(r"\$\w+", "x", p.split("?")[0])
    scen_ac |= set(re.findall(r"AC-N?\d+\.\d+", req))
    for op in ops:
        if op["method"] == method and op["rx"].match(p):
            scen_by_op[op["id"]].append(sid)
            break

# --- Критерії SRS -------------------------------------------------------
srs_ac = re.findall(r"^- \*\*(AC-N?\d+\.\d+)\.\*\*", open(SRS, encoding="utf-8").read(), re.M)
op_ac = {a for op in ops for a in op["ac"]}

# --- Вимоги → операції --------------------------------------------------
primary, side = defaultdict(list), defaultdict(list)
for op in ops:
    for r in op["req"]:
        primary[r].append(op["id"])
    for r in op["side"]:
        side[r].append(op["id"])

# --- spec/traceability.csv ----------------------------------------------
raw = open(TRACE, "rb").read()
bom = raw.startswith(b"\xef\xbb\xbf")
text = raw.decode("utf-8-sig")
nl = "\r\n" if "\r\n" in text else "\n"
lines = text.split(nl)
trailing = lines[-1] == ""
if trailing:
    lines = lines[:-1]
rows = [l.split(";") for l in lines]
header = rows[0]
if "API" not in header:
    at = header.index("Тікет") + 1
    for r in rows:
        r.insert(at, "")
    header = rows[0]
    header[at] = "API"
col_api, col_notes = header.index("API"), header.index("Примітки")

fr_rows = [r[0] for r in rows[1:] if r[0].startswith("FR-")]
uncovered = []
for r in rows[1:]:
    req = r[0]
    parts = []
    if primary.get(req):
        parts.append(", ".join(primary[req]))
    if side.get(req):
        parts.append("наслідок: " + ", ".join(side[req]))
    r[col_api] = " | ".join(parts)
    if req.startswith("FR-") and not parts:
        uncovered.append(req)
        if AUTOMATIC_NOTE not in r[col_notes]:
            r[col_notes] = (r[col_notes].rstrip() + " " + AUTOMATIC_NOTE).strip()

bad = [r[0] for r in rows if any(";" in c for c in r)]
if bad:
    sys.exit(f"у клітинках є ';' (рядки {', '.join(bad)}) — файл не записано")
out = nl.join(";".join(r) for r in rows) + (nl if trailing else "")
open(TRACE, "wb").write((b"\xef\xbb\xbf" if bom else b"") + out.encode("utf-8"))

# --- docs/api-traceability.md -------------------------------------------
md = []
md.append("# Простежуваність REQ-ID ↔ API operations\n")
md.append("Згенеровано `docs/scripts/api_traceability.py` з `api/openapi.yaml` "
          "(розширення `x-req-ids`, `x-side-effects`, `x-acceptance-criteria`, "
          "`x-roles`) і `tests/contract/run-scenarios.ps1`. Вручну не редагувати.\n")
md.append("## 1. Операції\n")
md.append("| № | operationId | Метод і шлях | REQ-ID | Наслідки | AC | Хто | Сценарії |")
md.append("|---|---|---|---|---|---|---|---|")
for i, op in enumerate(ops, 1):
    md.append("| {} | `{}` | {} `{}` | {} | {} | {} | {} | {} |".format(
        i, op["id"], op["method"], op["path"],
        ", ".join(op["req"]) or "—",
        ", ".join(op["side"]) or "—",
        len(op["ac"]),
        ", ".join(op["roles"]) or "—",
        ", ".join(scen_by_op.get(op["id"], [])) or "—"))

md.append("\n## 2. Покриття функціональних вимог\n")
md.append("| Вимога | Основна операція | Операції, що спричиняють наслідки |")
md.append("|---|---|---|")
for req in sorted(fr_rows, key=fr_key):
    md.append("| {} | {} | {} |".format(
        req,
        ", ".join(f"`{o}`" for o in primary.get(req, [])) or "—",
        ", ".join(f"`{o}`" for o in side.get(req, [])) or "—"))

md.append("\n## 3. Вимоги без операцій\n")
if uncovered:
    md.append("| Вимога | Чому немає операції |")
    md.append("|---|---|")
    for req in uncovered:
        md.append(f"| {req} | {AUTOMATIC_NOTE} |")
else:
    md.append("Немає.")

nfr = sorted({r for op in ops for r in op["req"] + op["side"] if r.startswith("NFR")}, key=fr_key)
md.append("\n## 4. Підсумок\n")
md.append(f"- Операцій: {len(ops)}; зі сценаріями: {sum(1 for o in ops if scen_by_op.get(o['id']))}.")
md.append(f"- Функціональних вимог: {len(fr_rows)}; з основною операцією: "
          f"{sum(1 for r in fr_rows if primary.get(r))}; лише як наслідок: "
          f"{sum(1 for r in fr_rows if side.get(r) and not primary.get(r))}; без операцій: {len(uncovered)}.")
md.append(f"- Нефункціональні вимоги в контракті: {', '.join(nfr) or '—'}.")
md.append(f"- Критеріїв прийняття в SRS: {len(srs_ac)}; позначено в операціях: "
          f"{len(op_ac & set(srs_ac))}; перевіряються сценаріями проти mock: {len(scen_ac & set(srs_ac))}.")
unknown = sorted(op_ac - set(srs_ac))
if unknown:
    md.append(f"- AC в операціях, яких немає в SRS: {', '.join(unknown)}.")
open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(md) + "\n")

print(f"операцій: {len(ops)}; FR: {len(fr_rows)}; без операцій: {', '.join(uncovered) or '—'}")
print(f"AC у SRS: {len(srs_ac)}; в операціях: {len(op_ac & set(srs_ac))}; у сценаріях: {len(scen_ac & set(srs_ac))}")
if unknown:
    print(f"УВАГА: AC в операціях, яких немає в SRS: {', '.join(unknown)}")
missing = [o["id"] for o in ops if not o["req"]]
if missing:
    print(f"УВАГА: операції без x-req-ids: {', '.join(missing)}")
print(f"записано: {OUT}, {TRACE}")
