#!/usr/bin/env python3
"""
Simple demo script to run the data integration engine without async database dependencies.
This demonstrates the weather data ingestion pipeline.
"""

import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

# Set up environment
os.environ.setdefault("DEV", "1")
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Demo coordinates
DEMO_COORDINATES = [
    {"name": "Santiago, Chile", "lat": -33.45, "lon": -70.6667},
    {"name": "São Paulo, Brazil", "lat": -23.55, "lon": -46.6333},
]


async def main():
    """Main demo function."""
    logger.info("🚀 Data Integration Engine Demo Starting...")
    logger.info("=" * 60)

    # Check configuration
    from preciagro.packages.engines.data_integration.config import settings

    logger.info(f"✅ Configuration Loaded")
    logger.info(
        f"   API Key Configured: {'Yes' if settings.OPENWEATHER_API_KEY else 'No'}")
    logger.info(f"   Database URL: {settings.DATABASE_URL}")
    logger.info(f"   Redis URL: {settings.REDIS_URL}")
    logger.info(f"   Rate Limit (QPS): {settings.INGEST_RATE_LIMIT_QPS}")

    try:
        # Import the connector
        from preciagro.packages.engines.data_integration.connectors.openweather import OpenWeatherConnector, OpenWeatherClient

        if not settings.OPENWEATHER_API_KEY:
            logger.error(
                "❌ OPENWEATHER_API_KEY not configured. Please set it in .env file")
            return

        logger.info("✅ OpenWeather Connector imported successfully")

        # Create client and connector
        client = OpenWeatherClient(api_key=settings.OPENWEATHER_API_KEY)
        connector = OpenWeatherConnector(client)

        logger.info("✅ OpenWeather Client initialized")
        logger.info("=" * 60)
        logger.info("📍 Starting data collection for demo locations:")

        # Fetch weather for each demo location
        for location in DEMO_COORDINATES:
            logger.info(f"\n📍 Fetching weather for {location['name']}...")
            logger.info(
                f"   Coordinates: {location['lat']}, {location['lon']}")

            try:
                # Call the async fetch method
                records = []
                async for record in connector.fetch_async(
                    cursor=None,
                    lat=location["lat"],
                    lon=location["lon"],
                    scope="hourly"
                ):
                    records.append(record)

                if records:
                    logger.info(f"✅ Data collected successfully")
                    logger.info(f"   Records returned: {len(records)}")

                    # Print a sample of the first record
                    if records:
                        sample_record = records[0]
                        logger.info(
                            f"   Sample record keys: {list(sample_record.keys())[:8]}")
                        if "temp" in sample_record:
                            logger.info(
                                f"   Temperature: {sample_record['temp']}°C")

                else:
                    logger.warning(f"⚠️  No data returned from API")

            except Exception as e:
                logger.error(f"❌ Error fetching data: {e}")

            # Respect rate limiting
            await asyncio.sleep(1.0 / max(1, settings.INGEST_RATE_LIMIT_QPS))

        logger.info("\n" + "=" * 60)
        logger.info("✅ Data Integration Engine Demo Complete!")
        logger.info("=" * 60)

    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        logger.error("Make sure all required dependencies are installed")
    except Exception as e:
        logger.error(f"❌ Error running demo: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
