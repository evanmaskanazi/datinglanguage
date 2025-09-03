import json
from typing import Any, Optional

class CacheManager:
    def __init__(self, redis_client):
        self.redis = redis_client
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            data = self.redis.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception:
            return None
    
    def set(self, key: str, value: Any, ttl: int = 300):
        """Set value in cache with TTL"""
        try:
            self.redis.setex(key, ttl, json.dumps(value))
            return True
        except Exception:
            return False
    
    def delete(self, key: str):
        """Delete key from cache"""
        try:
            self.redis.delete(key)
            return True
        except Exception:
            return False
