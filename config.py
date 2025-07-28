import os

MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb+srv://E_Learning:Wisdom67@cluster0.wq5zn4m.mongodb.net/elearn_demo?retryWrites=true&w=majority&appName=Cluster0")
SECRET_KEY = os.environ.get("SECRET_KEY", "7dec11d5501dc512207d0c9ac2e5ecd96afe8ff6daf1ce2c")  # Change this in production
MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "True").lower() in ['true', '1', 't']
MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "wisdomfrancis67@gmail.com")
MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "pulr ptkg fesp zcyt")
MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "wisdomfrancis67@gmail.com")
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
