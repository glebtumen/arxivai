from redis import Redis
from rq import Queue
from .config import settings

redis_conn = Redis.from_url(settings.redis_url)
item_queue = Queue("items", connection=redis_conn)