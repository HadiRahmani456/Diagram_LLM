# app/core/rate_limit.py
from fastapi import HTTPException, Request
from datetime import datetime, timedelta
from collections import defaultdict
import asyncio

class RateLimiter:
    def __init__(self):
        self.requests = defaultdict(list)
        self.daily_limits = {
            "free": 5,        # ۵ دیاگرام رایگان در روز
            "premium": 50,    # ۵۰ دیاگرام برای پرمیوم
            "enterprise": float("inf")  # نامحدود برای سازمانی
        }
    
    async def check_limit(self, user_id: str, plan: str = "free"):
        """بررسی محدودیت مصرف روزانه"""
        now = datetime.now()
        # حذف رکوردهای قدیمی
        self.requests[user_id] = [
            req_time for req_time in self.requests[user_id]
            if req_time > now - timedelta(days=1)
        ]
        
        # بررسی محدودیت
        if len(self.requests[user_id]) >= self.daily_limits.get(plan, 5):
            raise HTTPException(
                status_code=429,
                detail=f"محدودیت روزانه شما ({self.daily_limits[plan]} دیاگرام) به پایان رسیده. لطفاً ارتقا دهید یا از حالت آفلاین استفاده کنید."
            )
        
        # ثبت درخواست جدید
        self.requests[user_id].append(now)
        return {
            "remaining": self.daily_limits[plan] - len(self.requests[user_id]),
            "total": self.daily_limits[plan],
            "mode": "online"
        }