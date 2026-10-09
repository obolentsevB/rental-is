# Контрактні сценарії rental-is проти mock API (Prism).
# Перед запуском у іншому вікні:
#   npx @stoplight/prism-cli mock api/openapi.yaml --port 4010 --errors
# Запуск з кореня репозиторію:
#   .\tests\contract\run-scenarios.ps1 | Set-Content logs\api-scenarios.log -Encoding utf8
# Для кожного сценарію порівнюються HTTP-статус і поле code тіла Problem;
# порушення контракту, які знайшов mock, виводяться із заголовка sl-violations.
param([string]$Base = 'http://127.0.0.1:4010')

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$utf8 = New-Object System.Text.UTF8Encoding $false
$tmp = Join-Path ([IO.Path]::GetTempPath()) 'rental-is-contract'
New-Item -ItemType Directory -Force $tmp | Out-Null

$L = '4fad7a6c-9e5b-4ac2-9d6b-7b8c9daebfc5'   # житло з booking.feature
$B = '6bcf9c8e-b07d-4ce4-9f8d-9daebfc0d1e7'   # бронювання
$turnover = '{"listingId":"' + $L + '","checkIn":"2027-06-12","checkOut":"2027-06-14","guestsCount":2}'
$shared   = '{"listingId":"' + $L + '","checkIn":"2027-06-11","checkOut":"2027-06-13","guestsCount":2}'
$tooMany  = '{"listingId":"' + $L + '","checkIn":"2027-06-12","checkOut":"2027-06-14","guestsCount":5}'
$noOut    = '{"listingId":"' + $L + '","checkIn":"2027-06-12","guestsCount":2}'
$listing  = '{"title":"Поділ","city":"Київ","address":"вул. Сагайдачного, 1","maxGuests":4,"pricePerNight":"1234.56","photos":[{"data":"R0lGODlhAQABAAAAACw="}]}'

$scenarios = @(
  @{ Id='P-01'; Req='FR-01, AC-01.2'; Name='Реєстрація, пароль 8 символів';     M='POST'; P='/users';            Auth=$false; Body='{"email":"maria@example.com","password":"kyiv2027"}'; Prefer=$null; Status=@(201); Code=$null }
  @{ Id='P-02'; Req='FR-01, AC-01.3'; Name='Вхід';                              M='POST'; P='/auth/session';     Auth=$false; Body='{"email":"maria@example.com","password":"kyiv2027"}'; Prefer=$null; Status=@(201); Code=$null }
  @{ Id='P-03'; Req='FR-05';          Name='Пошук за містом, датами, особами';  M='GET';  P='/listings?city=%D0%9A%D0%B8%D1%97%D0%B2&checkIn=2027-06-12&checkOut=2027-06-14&guestsCount=2'; Auth=$false; Body=$null; Prefer=$null; Status=@(200); Code=$null }
  @{ Id='P-04'; Req='FR-08, AC-08.1'; Name='Заїзд у день виїзду попереднього';  M='POST'; P='/bookings';         Auth=$true;  Body=$turnover; Prefer='code=201, example=checkin-on-previous-checkout'; Status=@(201); Code=$null }
  @{ Id='P-05'; Req='FR-09';          Name='Підтвердження власником';           M='POST'; P="/bookings/$B/confirm"; Auth=$true; Body=$null; Prefer=$null; Status=@(200); Code=$null }
  @{ Id='P-06'; Req='FR-12';          Name='Мої поїздки';                       M='GET';  P='/bookings?role=guest'; Auth=$true;  Body=$null; Prefer=$null; Status=@(200); Code=$null }
  @{ Id='P-07'; Req='FR-17';          Name='Відгук про завершене бронювання';   M='POST'; P="/bookings/$B/reviews"; Auth=$true; Body='{"rating":5,"text":"Чисто, тихо, господиня на зв''язку."}'; Prefer=$null; Status=@(201); Code=$null }
  @{ Id='N-01'; Req='FR-08, AC-08.2'; Name='Спільна ніч';                       M='POST'; P='/bookings';         Auth=$true;  Body=$shared;   Prefer='code=409, example=dates-unavailable';   Status=@(409); Code='DATES_UNAVAILABLE' }
  @{ Id='N-02'; Req='FR-01, AC-01.7'; Name='Заблокований користувач';           M='POST'; P='/bookings';         Auth=$true;  Body=$turnover; Prefer='code=403, example=account-blocked';     Status=@(403); Code='ACCOUNT_BLOCKED' }
  @{ Id='N-03'; Req='FR-01, AC-01.2'; Name='Пароль із 7 символів';              M='POST'; P='/users';            Auth=$false; Body='{"email":"maria@example.com","password":"kyiv202"}'; Prefer=$null; Status=@(422); Code='VALIDATION_FAILED' }
  @{ Id='N-04'; Req='FR-01, AC-01.4'; Name='Запит без входу';                   M='POST'; P='/bookings';         Auth=$false; Body=$turnover; Prefer=$null; Status=@(401); Code='UNAUTHENTICATED' }
  @{ Id='N-05'; Req='FR-07, AC-07.3'; Name='Осіб більше за максимум';           M='POST'; P='/bookings';         Auth=$true;  Body=$tooMany;  Prefer='code=422, example=guests-out-of-range'; Status=@(422); Code='GUESTS_OUT_OF_RANGE' }
  @{ Id='N-06'; Req='FR-07, AC-07.4'; Name='Власник бронює своє житло';         M='POST'; P='/bookings';         Auth=$true;  Body=$turnover; Prefer='code=403, example=own-listing';         Status=@(403); Code='OWN_LISTING' }
  @{ Id='N-07'; Req='FR-02, ADD-01';  Name='Порушення вимог до фото';           M='POST'; P='/listings';         Auth=$true;  Body=$listing;  Prefer='code=422, example=photo-invalid';       Status=@(422); Code='PHOTO_INVALID' }
  @{ Id='C-01'; Req='контракт';       Name='Без обов''язкового checkOut (mock)'; M='POST'; P='/bookings';         Auth=$true;  Body=$noOut;    Prefer=$null; Status=@(422); Code='VALIDATION_FAILED' }
  @{ Id='N-08'; Req='FR-09';          Name='Підтвердження скасованого';         M='POST'; P="/bookings/$B/confirm"; Auth=$true; Body=$null; Prefer='code=409, example=state-conflict'; Status=@(409); Code='STATE_CONFLICT' }
)

$commit = (git rev-parse --short HEAD) 2>$null
"Протокол контрактних сценаріїв rental-is"
"Дата: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz'); коміт: $commit; mock: $Base"
"Специфікація: api/openapi.yaml; сценарії: P — позитивні, N — негативні, C — перевірка контракту mock-ом"
''
$pass = 0; $fail = 0
foreach ($s in $scenarios) {
  $out = Join-Path $tmp "$($s.Id).json"
  if (Test-Path $out) { Remove-Item $out }
  $hdr = Join-Path $tmp "$($s.Id).headers.txt"
  $a = @('-s', '-D', $hdr, '-o', $out, '-w', '%{http_code}', '-X', $s.M, "$Base$($s.P)",
         '-H', 'Accept: application/json, application/problem+json')
  if ($s.Auth)   { $a += @('-H', 'Authorization: Bearer test-token') }
  if ($s.Prefer) { $a += @('-H', "Prefer: $($s.Prefer)") }
  if ($s.Body) {
    $in = Join-Path $tmp "$($s.Id).req.json"
    [IO.File]::WriteAllText($in, $s.Body, $utf8)
    $a += @('-H', 'Content-Type: application/json', '--data-binary', "@$in")
  }
  $status = [int](& curl.exe @a)
  $code = ''
  if (Test-Path $out) {
    $raw = [IO.File]::ReadAllText($out, $utf8)
    if ($raw) { try { $code = [string](($raw | ConvertFrom-Json).code) } catch { } }
  }
  $viol = ''
  if (Test-Path $hdr) {
    $line = Select-String -Path $hdr -Pattern '^sl-violations:' -Encoding utf8 | Select-Object -First 1
    if ($line) { $viol = $line.Line.Substring(15).Trim() }
  }
  $ok = ($s.Status -contains $status) -and (-not $s.Code -or $code -eq $s.Code)
  if ($ok) { $pass++ } else { $fail++ }
  $expected = ($s.Status -join '/') + $(if ($s.Code) { " $($s.Code)" } else { '' })
  $actual   = "$status" + $(if ($code) { " $code" } else { '' })
  '{0}  {1}  очікувано {2,-25} отримано {3,-25} {4} ({5})' -f `
    $(if ($ok) { 'PASS' } else { 'FAIL' }), $s.Id, $expected, $actual, $s.Name, $s.Req
  if ($viol) { "      порушення контракту (sl-violations): $viol" }
}
''
"Разом: $($scenarios.Count); PASS: $pass; FAIL: $fail"
if ($fail -gt 0) { exit 1 }
