# PowerShell script to run docker-compose and integration tests
# Run from project root
# Starts DB + Redis, waits a bit, applies alembic migrations, then runs pytest integration tests

try {
	docker version | Out-Null
} catch {
	Write-Error "Docker does not appear to be running or accessible. Ensure Docker Desktop is running and you can run docker commands."
	exit 1
}

docker-compose up -d postgres redis
Start-Sleep -Seconds 5
# ensure alembic uses DATABASE_URL from env
$env:DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/preciagro"
alembic upgrade head

# run the integration test (path inside package)
pytest -q preciagro/packages/engines/data_integration/tests/test_integration_db_redis.py

Write-Output "Integration run complete"
