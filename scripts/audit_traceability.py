"""Аудит матриці простежуваності spec/traceability.csv.

Скрипт лише читає файли й друкує звіт у Markdown, нічого не змінюючи. Перевірки:

1. порожні обов'язкові зв'язки для реалізованих вимог;
2. ідентифікатори в матриці, яких немає в SRS і адендумах, і навпаки;
3. тести з матриці, яких немає в ``pytest --collect-only``, і зібрані тести без вимог;
4. модулі й розділи документації з матриці, яких не існує;
5. операції з колонки «API», яких немає в ``api/openapi.yaml``.

Клітинка «Тест», що починається з «Не перевірено у v1», — це явно позначена прогалина. Вона не
вважається порожнім зв'язком, але потрапляє в окремий інформаційний розділ звіту.

Запуск із кореня репозиторію::

    python scripts/audit_traceability.py > logs/traceability-audit.md

Код виходу 1 означає, що аудит щось знайшов.
"""

import csv
import io
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
MATRIX = ROOT / "spec/traceability.csv"
SRS = ROOT / "spec/srs.md"
ADDENDA = sorted((ROOT / "spec/addenda").glob("ADD-*.md"))
CONTRACT = ROOT / "api/openapi.yaml"
API_HTML = ROOT / "docs/api.html"

NOT_IMPLEMENTED = "Не реалізовано у v1"
PROCESS = "Процесна вимога"
NOT_VERIFIED = "Не перевірено у v1"
NO_OPERATION = "операції немає"
REQ_DEF = re.compile(r"^#{2,4} (?:\d+\. Вимога )?((?:FR|NFR)-[A-Z0-9-]*\d)\b", re.M)
AC_DEF = re.compile(r"^\s*- \*\*(AC-[A-Z0-9.-]*\d)", re.M)
ID_LIST = re.compile(r"\b(?:FR|NFR|AC)-[A-Z0-9.-]*\d")


def read_matrix() -> tuple[list[str], list[dict[str, str]]]:
    """Читає матрицю.

    Returns:
        Назви колонок і рядки як словники «колонка → значення».
    """
    text = MATRIX.read_bytes().decode("utf-8-sig")
    rows = list(csv.reader(io.StringIO(text, newline=""), delimiter=";"))
    return rows[0], [dict(zip(rows[0], row, strict=True)) for row in rows[1:]]


def spec_ids() -> tuple[set[str], set[str]]:
    """Збирає ідентифікатори вимог і критеріїв з SRS та адендумів.

    Returns:
        Ідентифікатори вимог FR/NFR і ідентифікатори критеріїв AC.
    """
    requirements, criteria = set(), set()
    for path in [SRS, *ADDENDA]:
        text = path.read_text(encoding="utf-8")
        requirements |= set(REQ_DEF.findall(text))
        criteria |= set(AC_DEF.findall(text))
    return requirements, criteria


def collected_tests() -> dict[str, int]:
    """Збирає тести через pytest без кешу.

    Returns:
        «файл::функція» → кількість тестів після параметризації.
    """
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    tests: dict[str, int] = {}
    for line in result.stdout.splitlines():
        match = re.match(r"tests/(?:[\w/]+/)?(\w+\.py)::(\w+)", line)
        if match:
            key = f"{match.group(1)}::{match.group(2)}"
            tests[key] = tests.get(key, 0) + 1
    return tests


def split_items(cell: str) -> list[str]:
    """Розбиває клітинку з переліком через « | »."""
    return [item.strip() for item in cell.split("|") if item.strip()]


def status(row: dict[str, str]) -> str:
    """Визначає статус рядка за колонкою «Примітки».

    Returns:
        ``not_implemented``, ``process`` або ``implemented``.
    """
    note = row["Примітки"]
    if note.startswith(NOT_IMPLEMENTED):
        return "not_implemented"
    if note.startswith(PROCESS):
        return "process"
    return "implemented"


def required_columns(row: dict[str, str]) -> list[str]:
    """Обов'язкові колонки реалізованого рядка.

    Критерії потрібні лише рядкам вимог. API не потрібен вимогам без операції (FR-10, FR-11)
    і нефункційним вимогам.
    """
    rid = row["REQ_ID"]
    columns = ["Тікет", "Тест", "Код", "Документація"]
    if not rid.startswith("AC-"):
        columns.insert(0, "Критерії")
    has_operation = NO_OPERATION not in row["Примітки"] and not rid.startswith(("NFR-", "AC-N"))
    if has_operation and rid not in ("FR-10", "FR-11"):
        columns.append("API")
    return columns


def headings_md(path: Path) -> list[str]:
    """Заголовки Markdown-файлу без символів #."""
    return re.findall(r"^#{1,6} (.+)$", path.read_text(encoding="utf-8"), re.M)


def headings_rst(path: Path) -> list[str]:
    """Заголовки reStructuredText-файлу (рядок над лінією з = або -)."""
    lines = path.read_text(encoding="utf-8").splitlines()
    return [
        lines[i - 1].strip() for i in range(1, len(lines)) if re.fullmatch(r"[=-]{3,}", lines[i])
    ]


def check_doc_item(item: str, html_ops: set[str]) -> list[str]:
    """Перевіряє одне посилання з колонки «Документація».

    Args:
        item: Посилання, наприклад «docs/user-guide.md §2.1, §2.3».
        html_ops: Операції, описані в docs/api.html.

    Returns:
        Описи проблем; порожній список, якщо посилання коректне.
    """
    path_text, _, rest = item.partition(" ")
    path_text = path_text.rstrip(":")
    path = ROOT / path_text
    if not path.exists():
        return [f"файлу `{path_text}` немає"]
    problems = []
    if path_text == "docs/api.html":
        for op in re.findall(r"\w+", rest):
            if op not in html_ops:
                problems.append(f"операції `{op}` немає в `docs/api.html`")
        return problems
    if path.suffix == ".md":
        heads = headings_md(path)
        for number in re.findall(r"§([\d.]+)", rest):
            if not any(h.startswith(f"{number}.") for h in heads):
                problems.append(f"розділу §{number} немає в `{path_text}`")
        if "вступ" in rest and not path.read_text(encoding="utf-8").split("\n## ")[0].strip():
            problems.append(f"вступу немає в `{path_text}`")
    if path.suffix == ".rst":
        heads = headings_rst(path)
        for title in re.findall(r"«([^»]+)»", rest):
            if title not in heads:
                problems.append(f"розділу «{title}» немає в `{path_text}`")
        text = path.read_text(encoding="utf-8")
        for module in re.findall(r"\b(src(?:\.\w+)*)\b", rest):
            if f"automodule:: {module}\n" not in text + "\n":
                problems.append(f"модуля `{module}` немає в `{path_text}`")
    if path.suffix == ".md":
        heads = headings_md(path)
        for title in re.findall(r"«([^»]+)»", rest):
            if title not in heads:
                problems.append(f"розділу «{title}» немає в `{path_text}`")
    return problems


def table(headers: list[str], rows: list[list[str]]) -> list[str]:
    """Формує таблицю Markdown."""
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join(cell.replace("|", "\\|") for cell in row) + " |" for row in rows]
    return out


def main() -> int:
    """Виконує аудит і друкує звіт.

    Returns:
        0, якщо нічого не знайдено, інакше 1.
    """
    _, rows = read_matrix()
    by_id = {row["REQ_ID"]: row for row in rows}
    requirements, criteria = spec_ids()
    contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    contract_ops = {
        op["operationId"]
        for item in contract["paths"].values()
        for op in item.values()
        if isinstance(op, dict) and "operationId" in op
    }
    html = API_HTML.read_text(encoding="utf-8")
    marker = "const __redoc_definition = "
    embedded, _ = json.JSONDecoder().raw_decode(html[html.index(marker) + len(marker) :])
    html_ops = {
        op["operationId"]
        for item in embedded["paths"].values()
        for op in item.values()
        if isinstance(op, dict) and "operationId" in op
    }
    tests = collected_tests()

    findings: dict[str, list[list[str]]] = {}

    # 1. Порожні обов'язкові зв'язки.
    empty = []
    for row in rows:
        if status(row) != "implemented":
            continue
        missing = [column for column in required_columns(row) if not row[column].strip()]
        if missing:
            empty.append([row["REQ_ID"], ", ".join(missing), row["Примітки"][:90]])
    findings["Порожні обов'язкові зв'язки реалізованих вимог"] = empty

    # 2. Ідентифікатори.
    matrix_req = {rid for rid in by_id if not rid.startswith("AC-")}
    matrix_ac_rows = {rid for rid in by_id if rid.startswith("AC-")}
    matrix_ac_listed = {ac for row in rows for ac in ID_LIST.findall(row["Критерії"])}
    findings["ID у матриці, яких немає в SRS і адендумах"] = (
        [[rid, "рядок матриці"] for rid in sorted(matrix_req - requirements)]
        + [[rid, "рядок матриці"] for rid in sorted(matrix_ac_rows - criteria)]
        + [[rid, "колонка «Критерії»"] for rid in sorted(matrix_ac_listed - criteria)]
    )
    findings["Вимоги SRS і адендумів, яких немає в матриці"] = [
        [rid, "немає рядка"] for rid in sorted(requirements - matrix_req)
    ] + [
        [rid, "немає ні рядка, ні згадки в «Критерії»"]
        for rid in sorted(criteria - matrix_ac_rows - matrix_ac_listed)
    ]

    # 3. Тести.
    referenced: set[str] = set()
    missing_tests, wrong_counts = [], []
    for row in rows:
        if status(row) == "not_implemented":
            continue
        if row["Тест"].startswith(NOT_VERIFIED):
            continue
        for item in split_items(row["Тест"]):
            name = re.sub(r" ×\d+$", "", item)
            referenced.add(name)
            if name not in tests:
                missing_tests.append([row["REQ_ID"], name])
                continue
            count = re.search(r"×(\d+)$", item)
            expected = int(count.group(1)) if count else 1
            if tests[name] != expected:
                wrong_counts.append(
                    [row["REQ_ID"], name, f"матриця ×{expected}, зібрано ×{tests[name]}"]
                )
    findings["Тести з матриці, яких немає в pytest --collect-only"] = missing_tests
    findings["Кількість параметризованих тестів не збігається з «×N»"] = wrong_counts
    findings["Зібрані тести без вимог у матриці"] = [
        [name, ""] for name in sorted(set(tests) - referenced)
    ]

    # 4. Модулі й документація.
    missing_modules, missing_docs = [], []
    for row in rows:
        for module in re.findall(r"src/[\w/]+\.py", row["Код"]):
            if not (ROOT / module).exists():
                missing_modules.append([row["REQ_ID"], module])
        for item in split_items(row["Документація"]):
            for problem in check_doc_item(item, html_ops):
                missing_docs.append([row["REQ_ID"], item, problem])
    findings["Модулі з колонки «Код», яких не існує"] = missing_modules
    findings["Розділи документації, яких не існує"] = missing_docs

    # 5. Операції.
    findings["Операції з колонки «API», яких немає в api/openapi.yaml"] = [
        [row["REQ_ID"], op]
        for row in rows
        for op in re.findall(r"\b[a-z]+[A-Z]\w*\b", row["API"])
        if op not in contract_ops
    ]

    columns = {
        "Порожні обов'язкові зв'язки реалізованих вимог": [
            "ID",
            "Порожні колонки",
            "Примітки (початок)",
        ],
        "ID у матриці, яких немає в SRS і адендумах": ["ID", "Де"],
        "Вимоги SRS і адендумів, яких немає в матриці": ["ID", "Що відсутнє"],
        "Тести з матриці, яких немає в pytest --collect-only": ["ID", "Тест"],
        "Кількість параметризованих тестів не збігається з «×N»": ["ID", "Тест", "Розбіжність"],
        "Зібрані тести без вимог у матриці": ["Тест", ""],
        "Модулі з колонки «Код», яких не існує": ["ID", "Модуль"],
        "Розділи документації, яких не існує": ["ID", "Посилання", "Проблема"],
        "Операції з колонки «API», яких немає в api/openapi.yaml": ["ID", "Операція"],
    }
    implemented = sum(status(row) == "implemented" for row in rows)
    out = [
        "# Аудит матриці простежуваності",
        "",
        "| Параметр | Значення |",
        "|----------|----------|",
        f"| Дата | {date.today().isoformat()} |",
        "| Скрипт | `python scripts/audit_traceability.py` (лише читає файли) |",
        "| Матриця | `spec/traceability.csv` |",
        f"| Рядків | {len(rows)}: реалізовано або частково — {implemented}, "
        f"не реалізовано у v1 — {sum(status(r) == 'not_implemented' for r in rows)}, "
        f"процесних — {sum(status(r) == 'process' for r in rows)} |",
        f"| Еталон ID | `spec/srs.md`, {', '.join(f'`spec/addenda/{p.name}`' for p in ADDENDA)}: "
        f"{len(requirements)} вимог, {len(criteria)} критеріїв |",
        f"| Тести | `pytest --collect-only`: {len(tests)} функцій, {sum(tests.values())} тестів |",
        f"| Операції | `api/openapi.yaml`: {len(contract_ops)} |",
        "",
        "Правила: рядок зі статусом «Не реалізовано у v1» на початку «Приміток» вважається "
        "поза обсягом, а рядок зі статусом «Процесна вимога» — процесним. Решта рядків "
        "вважаються реалізованими повністю або частково. Для них обов'язкові «Тікет», «Тест», "
        "«Код» і «Документація». Рядки вимог мають ще й «Критерії». «API» обов'язкова для "
        "функціональних вимог з операцією, крім FR-10 і FR-11, які операцій не мають. "
        "«Тест» зі статусом «Не перевірено у v1» — явна прогалина, а не порожній зв'язок.",
        "",
        "## Підсумок",
        "",
        *table(
            ["Перевірка", "Знайдено"], [[name, str(len(items))] for name, items in findings.items()]
        ),
    ]
    for name, items in findings.items():
        out += ["", f"## {name}", ""]
        out += table(columns[name], items) if items else ["Нічого не знайдено."]
    gaps = [[row["REQ_ID"], row["Тест"]] for row in rows if row["Тест"].startswith(NOT_VERIFIED)]
    out += ["", "## Явно позначені прогалини (інформаційно)", ""]
    out += table(["ID", "Тест"], gaps) if gaps else ["Немає."]
    print("\n".join(out))
    return 1 if any(findings.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
