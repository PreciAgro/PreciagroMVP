Set-Location 'C:\Users\tinot\Desktop\PreciagroMVP\preciagro\packages\engines\data_integration'
$env:PYTHONPATH = (Get-Location).Path
# Use an in-memory async sqlite DB for tests to avoid requiring asyncpg
$env:DATABASE_URL = 'sqlite+aiosqlite:///:memory:'
pytest -q tests
