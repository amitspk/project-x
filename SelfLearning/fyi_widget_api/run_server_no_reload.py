"""Run the API Service without reload."""

import uvicorn
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8005,
        reload=False,  # Disable reload to avoid multiprocessing issues
        log_level="info"
    )

