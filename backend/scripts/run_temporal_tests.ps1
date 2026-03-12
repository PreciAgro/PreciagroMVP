Set-Location 'C:\Users\tinot\Desktop\PreciagroMVP'
# Use in-memory sqlite for temporal_logic tests to avoid asyncpg
$env:DATABASE_URL = 'sqlite+aiosqlite:///:memory:'
pytest -q .\preciagro\packages\engines\temporal_logic\tests
