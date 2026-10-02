import os


class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./dev.db")
    jwt_secret: str = os.getenv("JWT_SECRET", "dev-secret-change-me")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))
    webhook_secret: str = os.getenv("PAYMENT_WEBHOOK_SECRET", "dev-webhook-secret")
    payment_success_rate: float = float(os.getenv("PAYMENT_SUCCESS_RATE", "0.8"))
    admin_email: str = os.getenv("ADMIN_EMAIL", "admin@example.com")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "Admin@12345")


settings = Settings()
