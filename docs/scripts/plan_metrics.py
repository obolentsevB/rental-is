# Розрахунки для docs/plan.md з docs/tickets.csv: години етапів і груп робіт,
# діаграма Ганта (Mermaid), критичний шлях по мережі етапів, розподіл годин
# між людиною й агентом.
# Запуск із кореня репозиторію:  python docs/scripts/plan_metrics.py
import sys
from collections import defaultdict, OrderedDict
from datetime import datetime, timedelta

CSV = "docs/tickets.csv"
START = datetime(2026, 10, 1)
HOURS_PER_WEEK = 12
CAL_H_PER_WORK_H = 7 * 24 / HOURS_PER_WEEK  # календарних годин на 1 год роботи

# Ключові групи робіт усередині етапів, у порядку виконання (топологічний).
GROUPS = OrderedDict([
    ("g0a", ("Е0", "Уточнення специфікації, адендум ADD-01", ["T-01", "T-02", "T-108"])),
    ("g0b", ("Е0", "Проєктування — стек, модель даних, API, ERROR", ["T-03", "T-04"])),
    ("g0c", ("Е0", "Макети мобільних екранів", ["T-05"])),
    ("g0d", ("Е0", "Інфраструктура розробки", ["T-06", "T-07", "T-08"])),
    ("g0e", ("Е0", "Traceability і Е0-GATE", ["T-92", "T-09"])),
    ("g1a", ("Е1", "Конфігурація і грошові розрахунки", ["T-10", "T-11", "T-16", "T-17"])),
    ("g1b", ("Е1", "Журнал подій і повідомлення", ["T-12", "T-13", "T-14", "T-15"])),
    ("g1c", ("Е1", "Вхід і захист облікових записів", ["T-18", "T-19", "T-20", "T-21"])),
    ("g1d", ("Е1", "Часові пояси", ["T-22", "T-23"])),
    ("g1e", ("Е1", "Верифікація NFR-11, traceability, gate Е1", ["T-93", "T-94", "T-24"])),
    ("g2a", ("Е2", "Картка житла", ["T-25", "T-26"])),
    ("g2b", ("Е2", "Перевірка доступності і відмови", ["T-27", "T-28", "T-29", "T-30"])),
    ("g2c", ("Е2", "Запит і закриття ночей", ["T-31", "T-32", "T-33", "T-34"])),
    ("g2d", ("Е2", "Пошук", ["T-35", "T-36"])),
    ("g2e", ("Е2", "Документація, валідація, gate Е2", ["T-95", "T-96", "T-97", "T-98", "T-37"])),
    ("g3a", ("Е3", "Підтвердження і конкурентність", ["T-38", "T-39", "T-40", "T-41"])),
    ("g3b", ("Е3", "Строк рішення і завершення", ["T-42", "T-43", "T-44", "T-45"])),
    ("g3c", ("Е3", "Скасування, повернення, виплати", ["T-46", "T-47", "T-48", "T-49", "T-50", "T-51"])),
    ("g3d", ("Е3", "Мої поїздки, доступ до журналу", ["T-52", "T-53", "T-54", "T-55"])),
    ("g3e", ("Е3", "Верифікація FR-08, валідація, gate Е3", ["T-99", "T-100", "T-101", "T-56"])),
    ("g4a", ("Е4", "Відгуки", ["T-57", "T-58", "T-59", "T-60"])),
    ("g4b", ("Е4", "Скарги і середня оцінка", ["T-61", "T-62", "T-63", "T-64"])),
    ("g4c", ("Е4", "Розмежування ролей", ["T-65", "T-66"])),
    ("g4d", ("Е4", "Traceability, gate Е4", ["T-102", "T-67"])),
    ("g5a", ("Е5", "Зняття оголошень і лічильник", ["T-68", "T-69", "T-70", "T-71"])),
    ("g5b", ("Е5", "Блокування", ["T-72", "T-73"])),
    ("g5c", ("Е5", "Спори і перерахунок повернення", ["T-74", "T-75", "T-76", "T-77"])),
    ("g5d", ("Е5", "Оскарження, доступ заблокованого", ["T-78", "T-79", "T-80", "T-81"])),
    ("g5e", ("Е5", "Конкурентність із модерацією", ["T-82", "T-83"])),
    ("g5f", ("Е5", "Верифікація FR-15 і NFR-01, документація, gate Е5", ["T-103", "T-104", "T-105", "T-106", "T-84"])),
    ("g6a", ("Е6", "Адаптивний інтерфейс", ["T-85", "T-86"])),
    ("g6b", ("Е6", "Продуктивність пошуку", ["T-87", "T-88"])),
    ("g6c", ("Е6", "Верифікація FR-23 і NFR-09", ["T-89", "T-90"])),
    ("g6d", ("Е6", "Traceability, приймання v1", ["T-107", "T-91"])),
])
GATE_MS = {"Е0": "Е0-GATE", "Е1": "Gate Е1", "Е2": "Gate Е2", "Е3": "Gate Е3",
           "Е4": "Gate Е4", "Е5": "Gate Е5", "Е6": "Приймання v1"}

# --- Дані -------------------------------------------------------------------
T = OrderedDict()
for line in open(CSV, encoding="utf-8").read().splitlines()[1:]:
    tid, stage, typ, ex, h, title, reqs, deps = line.split(";")
    T[tid] = dict(stage=stage, type=typ, exec=ex, h=float(h.replace(",", ".")),
                  deps=deps.split())
stages = list(OrderedDict.fromkeys(t["stage"] for t in T.values()))

group_of = {}
for g, (_, _, ids) in GROUPS.items():
    for i in ids:
        assert i not in group_of, f"{i} у двох групах"
        group_of[i] = g
missing = [i for i in T if i not in group_of]
assert not missing, f"тікети без групи: {missing}"
gh = {g: sum(T[i]["h"] for i in ids) for g, (_, _, ids) in GROUPS.items()}
sh = {s: sum(t["h"] for t in T.values() if t["stage"] == s) for s in stages}
for s in stages:
    assert abs(sum(gh[g] for g, v in GROUPS.items() if v[0] == s) - sh[s]) < 1e-9

def fmt(x):
    return f"{x:g}".replace(".", ",")

# Логічні залежності груп усередині етапу — з колонки «Залежить від».
gdeps = defaultdict(set)
for tid, t in T.items():
    for d in t["deps"]:
        a, b = group_of[tid], group_of[d]
        if a != b and GROUPS[a][0] == GROUPS[b][0]:
            gdeps[a].add(b)

print("## 1. Етапи і групи робіт")
print("| Етап | Група | Тікети | Год |")
print("|---|---|---|---|")
for g, (s, name, ids) in GROUPS.items():
    print(f"| {s} | {name} | {', '.join(ids)} | {fmt(gh[g])} |")
cum = 0
print("\n| Етап | Год | Наростаюче | Тижнів наростаюче | Строк |")
print("|---|---|---|---|---|")
for s in stages:
    cum += sh[s]
    x = cum * 7 / HOURS_PER_WEEK
    days = (int(x) if x == int(x) else int(x) + 1) - 1
    print(f"| {s} | {fmt(sh[s])} | {fmt(cum)} | {cum / HOURS_PER_WEEK:.1f} | {(START + timedelta(days=days)):%Y-%m-%d} |")
print(f"| разом | {fmt(sum(sh.values()))} | | | |")

# --- Ганта ------------------------------------------------------------------
print("\n## 2. Mermaid gantt")
print("```mermaid\ngantt\n    title rental-is — план реалізації (12 год/тиждень)\n"
      "    dateFormat YYYY-MM-DD\n    axisFormat %d.%m\n")
prev_ms = None
prev_g = None
for s in stages:
    print(f"    section {s}")
    for g, (gs, name, ids) in GROUPS.items():
        if gs != s:
            continue
        logical = sorted(gdeps[g])
        after = list(logical)
        if prev_g and prev_g not in after:
            after.append(prev_g)          # один виконавець: група після попередньої
        if prev_ms and not logical:
            after = [prev_ms] + [a for a in after if a != prev_ms]
        dur = int(round(gh[g] * CAL_H_PER_WORK_H))
        start = "2026-10-01" if prev_g is None else "after " + " ".join(after)
        note = f"логічно після: {', '.join(logical) if logical else (prev_ms or '—')}"
        print(f"    %% {g}: {fmt(gh[g])} год; {note}")
        print(f"    {name} :{g}, {start}, {dur}h")
        prev_g = g
    ms = "m" + s[1]
    print(f"    {GATE_MS[s]} :milestone, {ms}, after {prev_g}, 0h\n")
    prev_ms = ms
print("```")

# --- Критичний шлях по мережі етапів -----------------------------------------
# Мережа етапів: кожен етап починається після gate попереднього (ланцюг).
print("\n## 3. CPM по мережі етапів (години)")
pred = {s: ([stages[i - 1]] if i else []) for i, s in enumerate(stages)}
ES, EF = {}, {}
for s in stages:
    ES[s] = max((EF[p] for p in pred[s]), default=0)
    EF[s] = ES[s] + sh[s]
end = max(EF.values())
succ = defaultdict(list)
for s, ps in pred.items():
    for p in ps:
        succ[p].append(s)
LS, LF = {}, {}
for s in reversed(stages):
    LF[s] = min((LS[n] for n in succ[s]), default=end)
    LS[s] = LF[s] - sh[s]
print("| Робота | Попередник | D | ES | EF | LS | LF | S | Критична |")
print("|---|---|---|---|---|---|---|---|---|")
for s in stages:
    S = LS[s] - ES[s]
    print(f"| {s} | {', '.join(pred[s]) or '—'} | {fmt(sh[s])} | {fmt(ES[s])} | {fmt(EF[s])} | "
          f"{fmt(LS[s])} | {fmt(LF[s])} | {fmt(S)} | {'так' if S == 0 else 'ні'} |")
print("Критичний шлях:", " → ".join(s for s in stages if LS[s] == ES[s]),
      f"= {fmt(end)} год = {end / HOURS_PER_WEEK:.1f} тижня")

# Найдовший логічний ланцюжок тікетів усередині етапу (без обмеження виконавців)
print("\n## 3а. Найдовший логічний ланцюжок усередині етапу")
print("| Етап | Сума годин | Найдовший ланцюжок | Ланцюжок |")
print("|---|---|---|---|")
tot_chain = 0
for s in stages:
    ids = [i for i in T if T[i]["stage"] == s]
    best = {}
    for i in ids:  # рядки CSV упорядковано топологічно
        ds = [d for d in T[i]["deps"] if d in best]
        p = max(ds, key=lambda d: best[d][0], default=None)
        best[i] = (T[i]["h"] + (best[p][0] if p else 0), (best[p][1] if p else []) + [i])
    L, chain = max(best.values(), key=lambda v: v[0])
    tot_chain += L
    print(f"| {s} | {fmt(sh[s])} | {fmt(L)} | {' → '.join(chain)} |")
print(f"| разом | {fmt(sum(sh.values()))} | {fmt(tot_chain)} | |")

# --- Людина й агент ------------------------------------------------------------
print("\n## 4. Години за виконавцем і типом (критичний шлях = усі етапи)")
by = defaultdict(float)
for t in T.values():
    by[(t["exec"], t["type"])] += t["h"]
types = sorted({k[1] for k in by})
print("| Тип | human | both | agent | Разом |")
print("|---|---|---|---|---|")
for ty in types:
    row = [by[(e, ty)] for e in ("human", "both", "agent")]
    print(f"| {ty} | " + " | ".join(fmt(x) for x in row) + f" | {fmt(sum(row))} |")
tot = [sum(v for (e, _), v in by.items() if e == ex) for ex in ("human", "both", "agent")]
print("| разом | " + " | ".join(fmt(x) for x in tot) + f" | {fmt(sum(tot))} |")
named = sum(v for (e, ty), v in by.items() if ty in ("spec", "gate", "validation"))
ver = sum(v for (e, ty), v in by.items() if ty == "verification")
print(f"\nspec + gate + validation: {fmt(named)} год; verification (both): {fmt(ver)} год")
print(f"людина мінімум (лише human): {fmt(tot[0])} год = {tot[0] / HOURS_PER_WEEK:.1f} тижня")
print(f"людина максимум (human + both): {fmt(tot[0] + tot[1])} год = {(tot[0] + tot[1]) / HOURS_PER_WEEK:.1f} тижня")
print(f"агент (лише agent): {fmt(tot[2])} год")
