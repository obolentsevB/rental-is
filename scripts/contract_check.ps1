# Контрактна перевірка schemathesis для операцій Listings і Bookings з токеном кожної ролі
# (logs/lab5-scope.md, пп. 11, 12). Сервер має бути запущений: python scripts/serve_contract.py
# Код виходу ненульовий, якщо хоча б один прогін знайшов невідповідності.

Set-Location (Join-Path $PSScriptRoot '..')
$env:PYTHONIOENCODING = 'utf-8'

$failed = @()
foreach ($token in 'guest-token', 'host-token', 'moderator-token') {
    Write-Output "=== $token ==="
    python -m schemathesis.cli run api/openapi.yaml `
        --url http://127.0.0.1:8765 `
        -H "Authorization: Bearer $token" `
        --include-tag Listings --include-tag Bookings `
        --exclude-checks positive_data_acceptance
    if ($LASTEXITCODE -ne 0) { $failed += $token }
}

if ($failed.Count -gt 0) {
    Write-Output "Невідповідності знайдено для: $($failed -join ', ')"
    exit 1
}
