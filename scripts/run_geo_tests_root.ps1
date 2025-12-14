Set-Location 'C:\Users\tinot\Desktop\PreciagroMVP'
# Use in-memory sqlite for geo_context tests
$env:DATABASE_URL = 'sqlite+aiosqlite:///:memory:'
pytest -q .\preciagro\packages\engines\geo_context\tests
