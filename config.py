import os
from os.path import abspath, dirname, join
from datetime import timedelta

# DIRECTORY CONFIGURATION
BASE_DIR = dirname(abspath(__file__))
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
TAXONOMY = {
    "Clothing": {
        "keywords": [],
        "sub_categories": {
            "T-shirt": ["t-shirt", "tee", "polo", "tshirt", "graphic tee", "v-neck", "crew neck"],
            "Shirt": ["shirt", "button-down", "flannel", "blouse", "collar", "oxford", "linen shirt", "dress shirt"],
            "Hoodie": ["hoodie", "sweatshirt", "sweater", "pullover", "jumper", "zip-up", "knitwear", "cardigan"],
            "Pants": ["pant", "trouser", "chino", "cargo", "jogger", "slacks", "sweatpant", "legging", "tights", "bottoms"],
            "Jeans": ["jean", "denim", "jeggings", "dungarees", "overalls", "ripped jeans", "skinny jeans"],
            "Dress": ["dress", "gown", "frock", "skirt", "maxi", "midi", "mini", "sundress", "cocktail", "evening wear"],
            "Activewear": ["activewear", "gym", "yoga", "fitness", "sport bra", "tracksuit", "shorts", "athletic", "performance"],
            "Top": ["top", "tank", "camisole", "crop", "bodysuit", "tunic", "vest", "bustier"]
        }
    }
}

# --- EXPANDED ATTRIBUTES ---
ATTRIBUTES = {
    "Color": [
        # Basic
        "Red", "Blue", "Green", "Yellow", "Black", "White", "Pink", "Purple", "Orange", "Grey", "Gray", "Brown",
        # Shades & Nuances
        "Beige", "Navy", "Teal", "Gold", "Silver", "Neon", "Cream", "Khaki", "Burgundy", "Charcoal",
        "Olive", "Maroon", "Mustard", "Lavender", "Coral", "Indigo", "Violet", "Cyan", "Magenta", 
        "Turquoise", "Salmon", "Peach", "Tan", "Ivory", "Mint", "Fuchsia", "Rust", "Mauve", "Lilac",
        "Crimson", "Emerald", "Sapphire", "Ruby", "Rose"
    ],
    "Fabric": [
        # Natural
        "Cotton", "Linen", "Silk", "Wool", "Leather", "Denim", "Canvas", "Hemp", "Bamboo", "Cashmere",
        # Synthetic / Blends
        "Polyester", "Nylon", "Spandex", "Rayon", "Viscose", "Acrylic", "Fleece", "Microfiber", "Lycra",
        # Textures / Weaves
        "Velvet", "Satin", "Suede", "Chiffon", "Knitted", "Lace", "Mesh", "Corduroy", "Flannel", 
        "Tweed", "Jersey", "Chambray", "Georgette", "Organza", "Tulle", "Poplin", "Sequin", 
        "Fur", "Faux Leather", "Sherpa", "Ribbed"
    ],
    "Style": [
        # Fits
        "Oversized", "Slim", "Fitted", "Loose", "Baggy", "Tight", "Flowy", "Tailored", "Relaxed", "Skinny",
        # Aesthetics
        "Vintage", "Retro", "Boho", "Bohemian", "Minimalist", "Streetwear", "Casual", "Formal", "Chic", 
        "Elegant", "Sporty", "Classic", "Modern", "Urban", "Hipster", "Rock", "Edgy", "Punk", "Goth", 
        "Preppy", "Grunge", "Y2K", "Athleisure", "Business Casual",
        # Details
        "Layered", "Cropped", "Combat", "Printed", "Striped", "Floral", "Plaid", "Checkered", 
        "Pleated", "Ruffled", "Sheer", "Basic", "Statement", "Sustainable", "Embroidered", "Distressed"
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