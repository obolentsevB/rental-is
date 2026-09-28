#!/usr/bin/env bash
# Створює GitHub-тікети з docs/tickets.csv, milestones Е0…Е6 зі строками
# і, за потреби, додає тікети на дошку GitHub Projects.
#
# Запуск із кореня репозиторію:
#   bash docs/scripts/create-issues.sh --dry-run            — лише показати, без звернень до GitHub
#   bash docs/scripts/create-issues.sh                      — створити тікети й milestones
#   bash docs/scripts/create-issues.sh --project            — те саме + дошка «rental-is — план реалізації»
#   bash docs/scripts/create-issues.sh --project="Назва"    — інша дошка
#   bash docs/scripts/create-issues.sh --limit=5            — лише перші 5 тікетів CSV (тестовий запуск)
#
# Для --project токен gh має мати область project: gh auth refresh -s project
# Повторний запуск безпечний: створені тікети записуються в docs/tickets-issues.csv
# і вдруге не створюються; з --project наявні тікети лише додаються на дошку.
set -euo pipefail

CSV=docs/tickets.csv
MAP=docs/tickets-issues.csv
START=2026-10-01        # старт робіт (docs/plan.md)
HOURS_PER_WEEK=12       # навантаження (docs/plan.md)
DEFAULT_PROJECT="rental-is — план реалізації"

DRY=""
PROJECT=""
LIMIT=""
for arg in "$@"; do
  case "$arg" in
    --dry-run)   DRY=1 ;;
    --project)   PROJECT="$DEFAULT_PROJECT" ;;
    --project=*) PROJECT="${arg#--project=}" ;;
    --limit=*)   LIMIT="${arg#--limit=}" ;;
    *) echo "Невідомий аргумент: $arg" >&2; exit 2 ;;
  esac
done
if [[ -n "$LIMIT" && ! "$LIMIT" =~ ^[1-9][0-9]*$ ]]; then
  echo "ПОМИЛКА: --limit очікує ціле число більше 0, отримано «$LIMIT»" >&2
  exit 2
fi

# --- Milestones: назви, межі курсу, строки -----------------------------------
declare -A MILESTONE=(
  [Е0]="Е0. Уточнення, проєктування, підготовка"
  [Е1]="Е1. Ядро: конфігурація, журнал, повідомлення, гроші, вхід"
  [Е2]="Е2. Оголошення, доступність, створення запиту, пошук"
  [Е3]="Е3. Життєвий цикл бронювання і розрахунки"
  [Е4]="Е4. Відгуки і розмежування ролей"
  [Е5]="Е5. Модерація, блокування, спори, оскарження"
  [Е6]="Е6. Інтерфейс, продуктивність, приймання"
)
milestone_desc() {
  case "$1" in
    Е0|Е1) echo "Реалізується в межах дисципліни; обов'язковий мінімум (docs/plan.md)" ;;
    *)     echo "Затверджений план; поза межами реалізації в курсі (docs/plan.md)" ;;
  esac
}

# Строк етапу: дата, до якої при HOURS_PER_WEEK вичерпується сукупна оцінка
# всіх етапів до нього включно (календарні тижні, вихідні окремо не враховуються).
declare -A DUE
cum=0
while read -r stage hours; do
  cum=$(awk -v c="$cum" -v h="$hours" 'BEGIN { print c + h }')
  days=$(awk -v c="$cum" -v w="$HOURS_PER_WEEK" \
           'BEGIN { x = c * 7 / w; e = (x == int(x)) ? x : int(x) + 1; print e - 1 }')
  DUE[$stage]=$(date -d "$START + $days days" +%F)
done < <(tail -n +2 "$CSV" | tr -d '\r' | awk -F';' '
  { h = $5; sub(",", ".", h); if (!($2 in s)) order[++n] = $2; s[$2] += h }
  END { for (i = 1; i <= n; i++) print order[i], s[order[i]] }')

declare -A ISSUE
if [[ -f "$MAP" ]]; then
  while IFS=';' read -r id num; do ISSUE[$id]=$num; done < "$MAP"
fi

if [[ -n "$DRY" ]]; then
  echo "--- Milestones (старт $START, $HOURS_PER_WEEK год/тиждень)"
  for s in Е0 Е1 Е2 Е3 Е4 Е5 Е6; do
    echo "$s: строк ${DUE[$s]:-без дати} — ${MILESTONE[$s]} — $(milestone_desc "$s")"
  done
  [[ -n "$PROJECT" ]] && echo "--- Дошка: «$PROJECT»"
  [[ -n "$LIMIT" ]] && echo "--- Обмеження: перші $LIMIT тікетів CSV"
  echo
else
  # Дошка: перевірити заздалегідь, щоб не зупинитися посеред створення тікетів
  if [[ -n "$PROJECT" ]]; then
    owner=$(gh repo view --json owner -q .owner.login)
    if ! gh project list --owner "$owner" --limit 100 --format json -q '.projects[].title' \
         | grep -qxF "$PROJECT"; then
      echo "ПОМИЛКА: дошку «$PROJECT» не знайдено у $owner" >&2
      exit 1
    fi
  fi

  # Мітки: створюються лише відсутні, наявні не змінюються
  existing=$(gh label list --limit 500 --json name -q '.[].name')
  ensure_label() {
    grep -qxF "$1" <<<"$existing" || gh label create "$1" --color "$2" --description "$3"
  }
  for t in spec design chore test feature verification validation docs gate addendum; do
    ensure_label "type:$t" "ededed" "Тип тікета (docs/workflow.md)"
  done
  for e in human agent both; do
    ensure_label "executor:$e" "c5def5" "Виконавець"
  done

  # Milestones: відсутні створюються; у наявних із тією самою назвою
  # оновлюються строк і опис (обидва визначає план). Етап без рядків у CSV
  # не має строку — milestone створюється без дати.
  existing_ms=$(gh api 'repos/{owner}/{repo}/milestones?state=all' --paginate \
                  -q '.[] | "\(.number);\(.title)"')
  for s in Е0 Е1 Е2 Е3 Е4 Е5 Е6; do
    ms_args=(-f description="$(milestone_desc "$s")")
    [[ -n "${DUE[$s]:-}" ]] && ms_args+=(-f due_on="${DUE[$s]}T12:00:00Z")
    num=$(awk -F';' -v t="${MILESTONE[$s]}" '$2 == t { print $1 }' <<<"$existing_ms")
    if [[ -n "$num" ]]; then
      gh api -X PATCH "repos/{owner}/{repo}/milestones/$num" "${ms_args[@]}" > /dev/null
    else
      gh api "repos/{owner}/{repo}/milestones" -f title="${MILESTONE[$s]}" "${ms_args[@]}" > /dev/null
    fi
  done
fi

# --- Додатковий опис для окремих тікетів ------------------------------------
extra_body() {
  case "$1" in
    T-01) echo "Рішення: docs/open-questions.md, OQ-04; журнал знань K-316–K-319, K-324, K-326. Зміни SRS — адендум ADD-01 (T-108)." ;;
    T-02) echo "Рішення: docs/open-questions.md, OQ-05; журнал знань K-320–K-322, K-325, K-327, K-329, K-330. Зміни SRS — адендум ADD-01 (T-108)." ;;
    T-108) cat <<'EOF'
Підстава: OQ-04, OQ-05; журнал знань K-316–K-330. SRS змінюється окремим кроком після PLAN-GATE.

### Зміни до SRS
- **FR-02.** Фотографії: від 1 до 10, формати JPEG і PNG, розмір одного файлу — до 5 МБ = 5 242 880 байтів включно; сумарний розмір окремо не обмежується. Будь-яке порушення вимог до фотографій, зокрема кількості, — відмова у збереженні картки житла з єдиним кодом PHOTO_INVALID.
  AC-02.1 у новому формулюванні: «Оголошення без назви або без адреси не створюється; без опису — створюється. Картка житла без фотографій, з 11 фотографіями, з файлом не у форматі JPEG чи PNG або з файлом розміром 5 242 881 байт не зберігається: повертається код PHOTO_INVALID, у журналі подій з'являється запис WARN із цим кодом. Картка з 10 фотографіями у форматах JPEG і PNG розміром рівно 5 242 880 байтів кожна зберігається.»
- **FR-18.** Модератор бачить перелік поданих і ще не розглянутих скарг на відгуки; подання скарги — повідомлення всім модераторам (FR-23) і запис INFO (FR-22).
- **FR-20.** Те саме для спорів.
- **FR-21.** Те саме для оскаржень блокування й автоматичного зняття. Повідомлення про оскарження блокування отримує й модератор, який заблокував; розглядати оскарження він, як і раніше, не може.
- **FR-22.** INFO: подання спору, скарги на відгук, оскарження. WARN: відмова у збереженні картки житла з кодом PHOTO_INVALID.
- **FR-23.** Нові рядки таблиці: подання спору, скарги на відгук, оскарження → усі модератори.

### Супутні зміни
- §1.2, рядок «Черга завдань модератора»: визначення за K-317 (призначення виконавця, пріоритети, обов'язковість розгляду); призначення конкретного модератора немає (K-326).
- §5.1: PHOTO_INVALID у переліку кодів відмов.
- §6 і spec/traceability.csv: нові й змінені критерії прийняття.

### Зачіпає тікети
T-03, T-25/T-26, T-61/T-62, T-76/T-77, T-78/T-79, T-89.
EOF
    ;;
  esac
}

# --- Створення тікетів -------------------------------------------------------
# Рядки docs/tickets.csv упорядковано так, що залежності йдуть раніше за тікет,
# тому перші N рядків (--limit) завжди мають усі свої залежності.
row=0
while IFS=';' read -r id stage type exec hours title reqs deps; do
  row=$((row + 1))
  if [[ -n "$LIMIT" ]] && (( row > LIMIT )); then
    echo "Обмеження --limit=$LIMIT: решту тікетів пропущено"
    break
  fi

  if [[ -n "${ISSUE[$id]:-}" ]]; then
    if [[ -n "$PROJECT" && -z "$DRY" ]]; then
      gh issue edit "${ISSUE[$id]}" --add-project "$PROJECT" > /dev/null
      echo "$id уже створено: #${ISSUE[$id]} — додано на дошку"
    else
      echo "$id уже створено: #${ISSUE[$id]}"
    fi
    continue
  fi

  ms="${MILESTONE[$stage]:-}"
  if [[ -z "$ms" ]]; then
    echo "ПОМИЛКА: $id має невідомий етап «$stage»" >&2
    exit 1
  fi

  blocked=()
  for d in $deps; do
    if [[ -n "$DRY" ]]; then
      blocked+=("#<$d>")
    elif [[ -n "${ISSUE[$d]:-}" ]]; then
      blocked+=("#${ISSUE[$d]}")
    else
      echo "ПОМИЛКА: $id залежить від $d, який ще не створено" >&2
      exit 1
    fi
  done

  body="**Тимчасовий ID:** $id · **Етап:** $stage · **Оцінка:** $hours люд.-год
**Вимоги / критерії:** $reqs"

  # NFR-02: коміти test:/feat: мають згадувати всі FR-xx тікета
  if [[ "$type" == "test" || "$type" == "feature" ]]; then
    frs=$({ grep -o 'FR-[0-9]\+' <<<"$reqs" || true; } | sort -u | paste -sd, - | sed 's/,/, /g')
    [[ -n "$frs" ]] && body+="
**Коміти мають згадувати:** $frs"
  fi

  extra=$(extra_body "$id")
  [[ -n "$extra" ]] && body+="

$extra"

  if (( ${#blocked[@]} )); then
    body+="

Blocked by: $(IFS=,; echo "${blocked[*]}" | sed 's/,/, /g')"
  fi

  args=(--title "$title" --body "$body"
        --label "type:$type" --label "executor:$exec" --milestone "$ms")
  [[ -n "$PROJECT" ]] && args+=(--project "$PROJECT")

  if [[ -n "$DRY" ]]; then
    printf '=== %s [type:%s, executor:%s] [milestone: %s]%s %s\n%s\n\n' \
      "$id" "$type" "$exec" "$ms" "${PROJECT:+ [дошка: $PROJECT]}" "$title" "$body"
    ISSUE[$id]="<$id>"
    continue
  fi

  url=$(gh issue create "${args[@]}")
  num=${url##*/}
  ISSUE[$id]=$num
  echo "$id;$num" >> "$MAP"
  echo "$id → #$num"
done < <(tail -n +2 "$CSV" | tr -d '\r')
