import os
import redis
from rq import Worker, Queue, Connection
from redisProxy import process_q
from redis import StrictRedis

listen = ['default']

DB_HOST = os.environ.get("DB_HOST", "redis://cache")
DB_PORT = os.environ.get("DB_PORT", "6379")

redis_db = StrictRedis(
    host=DB_HOST,
    port=DB_PORT,
)
redis_url = os.getenv('REDISTOGO_URL', 'redis://cache:6379')

conn = redis.from_url(redis_url)

if __name__ == '__main__':
    with Connection(conn):
        worker = Worker(list(map(Queue, listen)))
        worker.work()