Set-Location 'C:\Users\tinot\Desktop\PreciagroMVP\preciagro\packages\engines\crop_intelligence'
$env:PYTHONPATH = (Get-Location).Path
pytest -q tests
