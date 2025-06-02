from functools import wraps
from flask import request, jsonify
import time
import logging
from datetime import datetime
from typing import Callable, Dict, Any
import threading
from config import config

logger = logging.getLogger(__name__)

class RateLimiter:
    def __init__(self, max_requests: int, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests: Dict[str, list] = {}
        self.lock = threading.Lock()

    def is_allowed(self, key: str) -> bool:
        with self.lock:
            now = time.time()
            if key not in self.requests:
                self.requests[key] = []

            # 清理过期的请求记录
            self.requests[key] = [req_time for req_time in self.requests[key]
                                if now - req_time < self.time_window]

            if len(self.requests[key]) >= self.max_requests:
                return False

            self.requests[key].append(now)
            return True

rate_limiter = RateLimiter(max_requests=config.API_RATE_LIMIT)

def rate_limit(f: Callable) -> Callable:
    """请求频率限制装饰器"""
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        if not rate_limiter.is_allowed(request.remote_addr):
            return jsonify({
                "error": "Too many requests",
                "message": "请求频率超限，请稍后再试"
            }), 429
        return f(*args, **kwargs)
    return decorated_function

def log_request(f: Callable) -> Callable:
    """请求日志记录装饰器"""
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        start_time = time.time()
        
        # 记录请求开始
        logger.info(f"Request started: {request.method} {request.path} "
                   f"from {request.remote_addr}")
        
        response = f(*args, **kwargs)
        
        # 计算请求处理时间
        duration = time.time() - start_time
        
        # 记录请求结束
        logger.info(
            f"Request completed: {request.method} {request.path} "
            f"from {request.remote_addr} "
            f"- Status: {response[1] if isinstance(response, tuple) else 200} "
            f"- Duration: {duration:.3f}s"
        )
        
        return response
    return decorated_function

def error_handler(f: Callable) -> Callable:
    """错误处理装饰器"""
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {f.__name__}: {str(e)}", exc_info=True)
            return jsonify({
                "error": "Internal server error",
                "message": "服务器内部错误，请稍后再试"
            }), 500
    return decorated_function 