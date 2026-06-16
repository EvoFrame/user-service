import asyncio

from redis.asyncio import Redis

from src.events.consumers import auth_user_registered

CONSUMERS = [auth_user_registered]


async def start_all_consumers(redis: Redis) -> None:
    for consumer in CONSUMERS:
        asyncio.create_task(consumer.run(redis))
