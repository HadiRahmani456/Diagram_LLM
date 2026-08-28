
import os
from pydantic_settings import BaseSettings  # دقت کنید که از pydantic_settings باشد

class Settings(BaseSettings):
    # تعریف متغیرها
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    COLAB_API_URL: str = os.getenv("COLAB_API_URL", "")

    class Config:
        env_file = ".env"  # این خط باعث می‌شود متغیرها از فایل .env خوانده شوند

# این خط حیاتی است! باید یک نمونه از کلاس بسازید
settings = Settings()
