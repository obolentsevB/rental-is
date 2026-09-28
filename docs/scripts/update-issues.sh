#!/usr/bin/env bash
# Дописує заходи з docs/risks.md в описи T-07 (#8), T-03 (#4), T-09 (#11)
# і пов'язує T-09 з новим тікетом T-109.
#
# Запуск із кореня репозиторію ПІСЛЯ створення T-109:
#   bash docs/scripts/create-issues.sh        — створює лише T-109 і оновлює строки milestones
#   bash docs/scripts/update-issues.sh        — цей скрипт
#
# Розділ вставляється перед рядком «Blocked by:». Якщо розділ із таким
# заголовком уже є, його текст замінюється; повторний запуск нічого не дублює.
set -euo pipefail

MAP=docs/tickets-issues.csv
PROJECT="rental-is — план реалізації"

t109=$(awk -F';' '$1 == "T-109" { print $2 }' "$MAP" | tr -d '\r')
if [[ -z "$t109" ]]; then
  echo "ПОМИЛКА: T-109 ще не створено; спершу bash docs/scripts/create-issues.sh" >&2
  exit 1
fi

set_section() {  # $1 — номер issue, $2 — заголовок розділу; текст — зі stdin
  local num=$1 marker=$2 body section tmp
  body=$(gh issue view "$num" --json body -q .body)
  section=$(cat)
  tmp=$(mktemp)
  # Прибрати наявний розділ із цим заголовком (до порожнього рядка включно)
  body=$(M="$marker" awk '
    $0 == ENVIRON["M"] { skip = 1; next }
    skip && /^$/       { skip = 0; next }
    !skip
  ' <<<"$body")
  SEC="$marker"$'\n'"$section" awk '
    /^Blocked by:/ && !done { print ENVIRON["SEC"]; print ""; done = 1 }
    { print }
    END { if (!done) { print ""; print ENVIRON["SEC"] } }
  ' <<<"$body" > "$tmp"
  gh issue edit "$num" --body-file "$tmp"
  rm -f "$tmp"
  echo "#$num: розділ «$marker» записано"
}

add_blocked_by() {  # $1 — номер issue, $2 — номер issue, від якого він залежить
  local num=$1 dep=$2 body tmp
  body=$(gh issue view "$num" --json body -q .body)
  if grep -qE "^Blocked by:.*#$dep([^0-9]|$)" <<<"$body"; then
    echo "#$num: залежність від #$dep уже є"
    return
  fi
  tmp=$(mktemp)
  if grep -q '^Blocked by:' <<<"$body"; then
    sed "s/^Blocked by:.*/&, #$dep/" <<<"$body" > "$tmp"
  else
    printf '%s\n\nBlocked by: #%s\n' "$body" "$dep" > "$tmp"
  fi
  gh issue edit "$num" --body-file "$tmp"
  rm -f "$tmp"
  echo "#$num: додано Blocked by #$dep"
}

# T-07 — протоколи прогонів (AI-02)
set_section 8 "### Відтворюваність властивісних тестів (AI-02, docs/risks.md)" <<'EOF'
- Для кожного властивісного тесту (зокрема AC-15.7) протокол прогону `logs/test-runs/<дата-час>_<хеш>.log` фіксує зерно генератора випадкових значень.
- Прогін можна повторити з тим самим зерном і отримати ті самі вхідні дані.
EOF

# T-03 — проєктування (TR-05)
set_section 4 "### Критерії вибору стеку (TR-05, docs/risks.md)" <<'EOF'
Рішення порівнює варіанти стеку за такими критеріями:
- транзакційна ізоляція або блокування на рівні житла, що не допускають двох бронювань у CONFIRMED чи COMPLETED з конфліктом за FR-08 при паралельних підтвердженнях (NFR-01);
- підміна системного годинника в тестах (SRS §2.5; FR-10, FR-11, AC-N07.3);
- база часових поясів із правилами переходу для Europe/Kyiv (NFR-07);
- досяжність p95 ≤ 500 мс для пошуку «місто + діапазон дат» на 10 000 оголошень і 100 000 бронювань (NFR-05).
EOF

# T-09 — Е0-GATE (TR-03): критерій GO і залежність від T-109
set_section 11 "### Критерій GO: оцінка часу перегляду (TR-03, docs/risks.md)" <<'EOF'
- [ ] Тікет T-109 закрито; строки в `docs/plan.md` перераховано.
EOF
add_blocked_by 11 "$t109"

# T-109 — на дошку (create-issues.sh без --project цього не робить)
gh issue edit "$t109" --add-project "$PROJECT" > /dev/null
echo "#$t109: додано на дошку «$PROJECT»"
