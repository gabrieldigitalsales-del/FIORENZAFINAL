import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "database.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
    STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")  # ✅ novo

    BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:5000")

    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "123456")

    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static/uploads")
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB