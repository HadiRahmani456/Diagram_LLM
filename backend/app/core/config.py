import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    APP_NAME: str = "IdeaDiagram AI"
    VERSION: str = "2.0.0"
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    COLAB_API_URL: str = os.getenv("COLAB_API_URL", "")
    
    FREE_DAILY_LIMIT: int = 10
    PREMIUM_DAILY_LIMIT: int = 50

settings = Settings()