"""Start script for ARQ worker."""
import asyncio
from arq import run_worker
from preciagro.packages.engines.temporal_logic.queue.worker import WorkerSettings

if __name__ == "__main__":
    run_worker(WorkerSettings)
