# Заповнює колонку «Тікет» у spec/traceability.csv номерами issue
# з docs/tickets-issues.csv; зв'язок вимога → тікет береться з колонки
# «Вимоги» в docs/tickets.csv. Інші колонки, BOM і кінці рядків не змінюються.
# Запуск із кореня репозиторію:  python docs/scripts/fill_traceability.py .
import re, sys
from collections import defaultdict

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
TRACE = f"{ROOT}/spec/traceability.csv"
TICKETS = f"{ROOT}/docs/tickets.csv"
ISSUES = f"{ROOT}/docs/tickets-issues.csv"
BLANKET = set()  # загальні тікети тепер вилучаються через EXCLUDED/OVERRIDE
# У матриці — лише тікети, що прямо реалізують, перевіряють, документують
# або уточнюють вимогу.
EXCLUDED = {"T-09",                                               # загальний gate
            "T-92", "T-94", "T-97", "T-101", "T-102", "T-106", "T-107"}  # оновлення traceability
OVERRIDE = {"T-91": "NFR-02, NFR-03, NFR-04"}  # прямо перевіряє AC-N02.x, AC-N03.1, AC-N04.1

raw = open(TRACE, "rb").read()
bom = raw.startswith(b"\xef\xbb\xbf")
text = raw.decode("utf-8-sig")
nl = "\r\n" if "\r\n" in text else "\n"
lines = text.split(nl)
trailing = lines[-1] == ""
if trailing:
    lines = lines[:-1]
header = lines[0].split(";")
col = header.index("Тікет")
rows = [l.split(";") for l in lines[1:]]
req_ids = [r[0] for r in rows]
all_fr = [r for r in req_ids if r.startswith("FR-")]

issue = dict(l.strip().split(";") for l in open(ISSUES, encoding="utf-8") if l.strip())

def expand(reqs):
    found, notes = set(), []
    if "усі FR і NFR" in reqs or "усі AC" in reqs:
        found |= set(req_ids)
    elif "усі FR" in reqs:
        found |= set(all_fr)
    for a, pa, b in re.findall(r"(FR|NFR)-(\d+)…(?:FR|NFR)-(\d+)", reqs):
        for n in range(int(pa), int(b) + 1):
            found.add(f"{a}-{n:02d}")
    found |= {m for m in re.findall(r"\b(?:FR|NFR)-\d+\b", reqs)}
    notes = re.findall(r"SRS §[\d.]+|idea §\d+|\bR\d\b|IR-\d+|K-\d+", reqs)
    return found, notes

by_req = defaultdict(set)
by_req_specific = defaultdict(set)
unknown, non_req = [], []
excluded_gate_links = []
for l in open(TICKETS, encoding="utf-8").read().splitlines()[1:]:
    f = l.split(";")
    tid, ttype, reqs = f[0], f[2], f[6]
    if tid in EXCLUDED:
        continue
    if tid in OVERRIDE:
        reqs = OVERRIDE[tid]
    if ttype == "gate" and " для " in reqs:
        reqs, dropped = reqs.split(" для ", 1)
        excluded_gate_links.append((tid, dropped))
    ids, notes = expand(reqs)
    for r in ids:
        if r not in req_ids:
            unknown.append((tid, r))
            continue
        by_req[r].add(int(issue[tid]))
        if tid not in BLANKET:
            by_req_specific[r].add(tid)
    if notes:
        non_req.append((tid, notes))

for r in rows:
    nums = sorted(by_req.get(r[0], ()))
    r[col] = ", ".join(f"#{n}" for n in nums)

out = nl.join([lines[0]] + [";".join(r) for r in rows]) + (nl if trailing else "")
open(TRACE, "wb").write((b"\xef\xbb\xbf" if bom else b"") + out.encode("utf-8"))

print("вимог у матриці:", len(req_ids))
print("вимог із тікетами:", sum(1 for r in req_ids if by_req.get(r)))
print("без жодного тікета:", [r for r in req_ids if not by_req.get(r)])
print("лише із загальних тікетів T-09/T-91/T-92/T-107:", [r for r in req_ids if not by_req_specific.get(r)])
print("ID, яких немає в матриці:", unknown)
print("посилання не на вимоги матриці:")
for tid, n in non_req:
    print("  ", tid, n)
import statistics
counts = [len(by_req.get(r, ())) for r in req_ids]
print("тікетів на вимогу: мін", min(counts), "макс", max(counts), "медіана", statistics.median(counts))
print("рівно один тікет:", [r for r, c in zip(req_ids, counts) if c == 1])
print("вилучені прив'язки gate після «для»:", excluded_gate_links)
for r in req_ids:
    print(f"  {r}: {len(by_req.get(r, ()))}  {sorted(by_req_specific.get(r, ()), key=lambda t: int(t[2:]))}")
