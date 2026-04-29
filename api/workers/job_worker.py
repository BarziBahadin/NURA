import asyncio
import logging

from core.job_queue import run_job_worker


logging.basicConfig(level=logging.INFO)


async def main() -> None:
    await run_job_worker(worker_name="standalone-worker")


if __name__ == "__main__":
    asyncio.run(main())
