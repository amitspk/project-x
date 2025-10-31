"""Run the Worker Service."""

import asyncio
import logging
from worker import main

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

if __name__ == "__main__":
    asyncio.run(main())

