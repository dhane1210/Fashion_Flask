import os
from os.path import abspath, dirname, join
from datetime import timedelta
from dotenv import load_dotenv

# DIRECTORY CONFIGURATION
BASE_DIR = dirname(abspath(__file__))

# Load environment variables from .env file
load_dotenv(join(BASE_DIR, '.env'))
DATA_DIR = join(BASE_DIR, "data")

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# FILE PATHS
PATHS = {
    "raw_csv": join(DATA_DIR, "raw_dataset.csv"),
    "processed_csv": join(DATA_DIR, "processed_data.csv")
}


# FLASK APP CONFIGURATION
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', f'sqlite:///{join(BASE_DIR, "trends.db")}')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT Configuration
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)

    # File Upload Configuration
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max file size
    ALLOWED_EXTENSIONS = {'csv'}


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    # In production, these MUST be set via environment variables
    if Config.SECRET_KEY == 'dev-secret-key-change-in-production':
        raise ValueError("SECRET_KEY must be set in production")
    if Config.JWT_SECRET_KEY == 'jwt-secret-change-in-production':
        raise ValueError("JWT_SECRET_KEY must be set in production")


# CLIENT TAXONOMY (Clothing Only)
PRODUCT_HIERARCHY = {
    "Clothing": [
        "T-shirt", "Shirt", "Hoodie", "Pants", "Jeans",
        "Dress", "Activewear", "Top"
    ]
}

# --- KEYWORD MAPPING ---
# This dictates how the system finds items in the text
TAXONOMY = {
    "Clothing": {
        "keywords": [],
        "sub_categories": {
            "T-shirt": ["t-shirt", "tee", "polo", "tshirt"],
            "Shirt": ["shirt", "button-down", "flannel", "blouse", "collar"],
            "Hoodie": ["hoodie", "sweatshirt", "sweater", "pullover", "jumper"],
            "Pants": ["pant", "trouser", "chino", "cargo", "jogger", "slacks"],
            "Jeans": ["jean", "denim", "jeggings"],
            "Dress": ["dress", "gown", "frock", "skirt", "maxi", "midi", "mini"],
            "Activewear": ["activewear", "gym", "yoga", "fitness", "legging", "sport bra", "tracksuit"],
            "Top": ["top", "tank", "camisole", "crop", "bodysuit"]
        }
    }
}

# ATTRIBUTES (Specific to Apparel)
ATTRIBUTES = {
    "Color": [
        "Red", "Blue", "Green", "Yellow", "Black", "White", "Pink", "Purple",
        "Orange", "Grey", "Beige", "Brown", "Navy", "Teal", "Gold", "Silver",
        "Neon", "Cream", "Khaki", "Burgundy", "Charcoal"
    ],
    "Fabric": [
        "Linen", "Denim", "Cotton", "Silk", "Wool", "Leather", "Mesh", "Velvet",
        "Polyester", "Satin", "Suede", "Chiffon", "Knitted", "Lace", "Cashmere", "Spandex"
    ],
    "Style": [
        "Oversized", "Slim", "Combat", "Retro", "Layered", "Cropped", "Fitted",
        "Vintage", "Boho", "Minimalist", "Streetwear", "Casual", "Formal", "Baggy",
        "Chic", "Sporty", "Elegant", "Printed", "Striped"
    ]
}

# AGE GROUP MAPPINGS
AGE_GROUPS = {
    "18-24": (18, 24),
    "25-34": (25, 34),
    "35-44": (35, 44),
    "45-54": (45, 54),
    "55+": (55, 100)
}

# USER ROLES
ROLES = {
    "ADMIN": "admin",
    "MANAGER": "manager",
    "OWNER": "owner"
}

# PREDICTION STATUS
PREDICTION_STATUS = {
    "PENDING": "pending",
    "APPROVED": "approved",
    "REJECTED": "rejected"
}