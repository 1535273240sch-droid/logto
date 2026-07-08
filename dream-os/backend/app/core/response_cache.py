"""Response Cache"""
import hashlib, time, logging
from typing import Optional
logger = logging.getLogger('dream-os.cache')

CACHED_RESPONSES = {
    '你好': '你好！有什么可以帮你的吗？',
    '你是谁': '我是 Dream OS AI 助手，可以帮你查询信息、执行命令、生成内容等。',
    'hello': 'Hello! How can I help you today?',
    'hi': 'Hi there! What can I do for you?',
    '谢谢': '不客气！有什么需要随时找我。',
}

class ResponseCache:
    def __init__(self, max_size=100, ttl=3600):
        self._cache = {}
        self._max_size = max_size
        self._ttl = ttl

    def get(self, prompt):
        clean = prompt.strip().lower()
        if clean in CACHED_RESPONSES:
            return CACHED_RESPONSES[clean]
        key = hashlib.md5(clean.encode()).hexdigest()
        entry = self._cache.get(key)
        if entry:
            ts, resp = entry
            if time.time() - ts < self._ttl:
                return resp
            del self._cache[key]
        return None

    def set(self, prompt, response):
        key = hashlib.md5(prompt.strip().lower().encode()).hexdigest()
        self._cache[key] = (time.time(), response)
        if len(self._cache) > self._max_size:
            oldest = min(self._cache.items(), key=lambda x: x[1][0])
            del self._cache[oldest[0]]

_response_cache = ResponseCache()
def get_response_cache():
    return _response_cache
