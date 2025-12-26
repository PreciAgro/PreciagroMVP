#!/usr/bin/env python3
"""
Production startup script for PreciAgro Data Integration Engine.
Runs the FastAPI server with all available engines and endpoints.

Usage:
    python run_production.py [--port 8000] [--host 0.0.0.0] [--reload]

This script:
1. Sets up environment configuration
2. Initializes all available engines
3. Starts the FastAPI server with Uvicorn
4. Gracefully handles missing dependencies
"""

import os
import sys
import argparse
import logging

# Set up environment early
os.environ.setdefault("DEV", "1")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Run PreciAgro Data Integration Engine"
    )
    parser.add_argument("--port", type=int, default=8000,
                        help="Port to run on (default: 8000)")
    parser.add_argument("--host", default="127.0.0.1",
                        help="Host to bind to (default: 127.0.0.1)")
    parser.add_argument("--reload", action="store_true",
                        help="Enable auto-reload on file changes")
    parser.add_argument("--workers", type=int, default=1,
                        help="Number of workers (default: 1)")

    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("🚀 PreciAgro Data Integration Engine - Production Mode")
    logger.info("=" * 70)

    # Display configuration
    logger.info(f"Configuration:")
    logger.info(f"  Host: {args.host}")
    logger.info(f"  Port: {args.port}")
    logger.info(f"  Auto-reload: {args.reload}")
    logger.info(f"  Workers: {args.workers}")
    logger.info("")

    # Try to import and validate configuration
    try:
        from preciagro.packages.engines.data_integration.config import settings as di_settings
        logger.info("✅ Data Integration Engine configuration loaded")
        logger.info(
            f"   - API Key configured: {'Yes' if di_settings.OPENWEATHER_API_KEY else 'No'}")
        logger.info(f"   - Database URL: {di_settings.DATABASE_URL}")
        logger.info(f"   - Redis URL: {di_settings.REDIS_URL}")
        logger.info(
            f"   - Rate Limit: {di_settings.INGEST_RATE_LIMIT_QPS} QPS")
    except Exception as e:
        logger.error(f"❌ Failed to load Data Integration config: {e}")
        sys.exit(1)

    # Try to import temporal config
    try:
        from preciagro.packages.engines.temporal_logic.config import config as temporal_config
        logger.info("✅ Temporal Logic Engine configuration loaded")
    except Exception as e:
        logger.warning(f"⚠️  Temporal Logic config not available: {e}")

    logger.info("")
    logger.info("=" * 70)
    logger.info("Starting FastAPI server...")
    logger.info("=" * 70)
    logger.info("")
    logger.info(f"📍 Server will be available at:")
    logger.info(f"   http://{args.host}:{args.port}")
    logger.info(f"   Health check: http://{args.host}:{args.port}/healthz")
    logger.info(f"   API docs: http://{args.host}:{args.port}/docs")
    logger.info(f"   Metrics: http://{args.host}:{args.port}/metrics")
    logger.info("")
    logger.info("Press CTRL+C to stop the server")
    logger.info("")

    # Build uvicorn command
    import subprocess

    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "preciagro.apps.api_gateway.main:app",
        "--host", args.host,
        "--port", str(args.port),
    ]

    if args.reload:
        cmd.append("--reload")

    if args.workers > 1 and not args.reload:
        cmd.extend(["--workers", str(args.workers)])

    # Set environment variables for subprocess
    env = os.environ.copy()
    env["DEV"] = "1"
    env["PYTHONPATH"] = "."

    try:
        subprocess.run(cmd, env=env)
    except KeyboardInterrupt:
        logger.info("\n✅ Server stopped gracefully")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Error running server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
