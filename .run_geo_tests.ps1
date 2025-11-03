Set-Location 'C:\Users\tinot\Desktop\PreciagroMVP\preciagro\packages\engines\geo_context'
$env:PYTHONPATH = (Get-Location).Path
# Use in-memory async sqlite to avoid asyncpg
$env:DATABASE_URL = 'sqlite+aiosqlite:///:memory:'
pytest -q tests
