import os
from os.path import abspath, dirname, join

# --- DIRECTORY CONFIGURATION ---
BASE_DIR = dirname(abspath(__file__))
DATA_DIR = join(BASE_DIR, "data")

# --- FILE PATHS ---
PATHS = {
    "raw_csv": join(DATA_DIR, "raw_dataset.csv"), 
    "processed_csv": join(DATA_DIR, "processed_data.csv")
}

# --- CLIENT TAXONOMY (Clothing Only) ---
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

# --- ATTRIBUTES (Specific to Apparel) ---
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