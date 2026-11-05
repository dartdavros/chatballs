"""Короткие Redis leases хранят лишь идентификаторы, никогда аудио/черновик."""

import hashlib
import secrets
from contextlib import contextmanager

from django.conf import settings
from redis import Redis
from redis.exceptions import RedisError

from chatballs.speech.errors import SpeechError

ACQUIRE = """
if redis.call('EXISTS', KEYS[1]) == 1 then return 0 end
for i = 2, #KEYS do
  if tonumber(redis.call('GET', KEYS[i]) or '0') >= tonumber(ARGV[i+1]) then return 0 end
end
redis.call('SET', KEYS[1], ARGV[1], 'EX', ARGV[2])
for i = 2, #KEYS do redis.call('INCR', KEYS[i]); redis.call('EXPIRE', KEYS[i], ARGV[2]) end
return 1
"""
RELEASE = """
if redis.call('GET', KEYS[1]) ~= ARGV[1] then return 0 end
redis.call('DEL', KEYS[1])
for i = 2, #KEYS do
  if tonumber(redis.call('GET', KEYS[i]) or '0') <= 1 then redis.call('DEL', KEYS[i])
  else redis.call('DECR', KEYS[i]) end
end
return 1
"""


@contextmanager
def recognition_lease(*, session_id: int, widget_id: int, integration_id: int, client_address: str, seconds=70):
    address = hashlib.sha256(client_address.encode()).hexdigest()
    keys = [f"speech:session:{session_id}", f"speech:widget:{widget_id}", f"speech:integration:{integration_id}", f"speech:address:{address}"]
    nonce = secrets.token_hex(16)
    with Redis.from_url(settings.CACHES["default"]["LOCATION"], socket_connect_timeout=2, socket_timeout=2) as client:
        try:
            if not client.eval(ACQUIRE, len(keys), *keys, nonce, seconds, 2, 4, 4):
                raise SpeechError("busy")
        except RedisError:
            raise SpeechError("busy") from None
        try:
            yield
        finally:
            try:
                client.eval(RELEASE, len(keys), *keys, nonce)
            except RedisError:
                pass  # Истечение lease гарантирует освобождение без durable очереди.
