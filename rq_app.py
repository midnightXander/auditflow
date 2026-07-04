import os
from redis import Redis
from rq import Queue

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
redis_conn = Redis.from_url(redis_url)

queue = Queue(connection=redis_conn)
print(f"Connected to Redis at {redis_url} and initialized RQ queue.", queue)
