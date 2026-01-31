import pandas as pd
import numpy as np
import os
import sys
from config import PATHS, TAXONOMY, ATTRIBUTES


def clean_text_simple(text):
    return str(text).lower()


def extract_category(text):
    text = clean_text_simple(text)

    clothing_rules = TAXONOMY["Clothing"]["sub_categories"]

    for sub_cat, keywords in clothing_rules.items():
        for keyword in keywords:
            # Add spaces to ensure whole-word matching
            if f" {keyword} " in f" {text} ":
                return "Clothing", sub_cat

    return "Uncategorized", "General"


def extract_attributes(text):
    text = clean_text_simple(text)
    found = {}

    for attr_type, keyword_list in ATTRIBUTES.items():
        found[attr_type] = "Unknown"

        for word in keyword_list:
            if f" {word.lower()} " in f" {text} ":
                found[attr_type] = word
                break

    return found


def assign_season(row):
    try:
        dt = pd.to_datetime(row['timestamp'])
        if 4 <= dt.month <= 8:
            return "SS26"
        else:
            return "FW26"
    except:
        return "Core/Evergreen"


def calculate_velocity_score(df):
    # Base popularity on count
    pop_score = df.groupby('Sub_Category')['text_content'].transform('count')

    # Add random growth factor for demo (replace with real algorithm in production)
    random_growth = np.random.randint(-10, 80, size=len(df))

    # Normalize to 0-100 scale
    velocity = ((pop_score + random_growth) / (pop_score.max() + 100)) * 100
    velocity = velocity.clip(10, 99).round(1)

    return velocity


def run_processor():
    print("=" * 60)
    print("Fashion Trends Data Processor")
    print("=" * 60)

    # Check if raw CSV exists
    if not os.path.exists(PATHS['raw_csv']):
        print(f"Error: Raw CSV not found at {PATHS['raw_csv']}")
        print("Please ensure the raw dataset is in the correct location.")
        return False

    try:
        # 1. Load raw data
        print(f"\nLoading raw data from: {PATHS['raw_csv']}")
        df = pd.read_csv(PATHS['raw_csv'])
        print(f"Loaded {len(df):,} rows")

        # 2. Extract categories
        print("\nExtracting product categories...")
        tag_results = df['text_content'].apply(extract_category)
        df['Category'] = [x[0] for x in tag_results]
        df['Sub_Category'] = [x[1] for x in tag_results]

        # 3. Filter for clothing only
        print("Filtering for Clothing items only...")
        initial_count = len(df)
        df = df[df['Category'] == "Clothing"].copy()
        filtered_count = len(df)
        print(f"Kept {filtered_count:,} Clothing items ({initial_count - filtered_count:,} removed)")

        if df.empty:
            print("Error: No clothing items found in dataset!")
            return False

        # 4. Extract attributes
        print("\nExtracting product attributes (Color, Fabric, Style)...")
        attr_results = df['text_content'].apply(extract_attributes)
        df['Color'] = [x['Color'] for x in attr_results]
        df['Fabric'] = [x['Fabric'] for x in attr_results]
        df['Style'] = [x['Style'] for x in attr_results]

        # 5. Assign seasons
        print("Assigning seasons (SS26/FW26)...")
        df['Season'] = df.apply(assign_season, axis=1)

        # 6. Calculate velocity scores
        print("⚡ Calculating velocity scores...")
        df['Velocity_Score'] = calculate_velocity_score(df)

        # 7. Save processed data
        print(f"\nSaving processed data to: {PATHS['processed_csv']}")

        # Ensure data directory exists
        os.makedirs(os.path.dirname(PATHS['processed_csv']), exist_ok=True)

        df.to_csv(PATHS['processed_csv'], index=False)

        # 8. Print summary statistics
        print("\n" + "=" * 60)
        print("Processing Summary")
        print("=" * 60)
        print(f"Total Rows: {len(df):,}")
        print(f"\nProduct Distribution:")
        print(df['Sub_Category'].value_counts().to_string())
        print(f"\nSeason Distribution:")
        print(df['Season'].value_counts().to_string())
        print(f"\nTop Colors:")
        top_colors = df[df['Color'] != 'Unknown']['Color'].value_counts().head(5)
        print(top_colors.to_string())
        print("\n" + "=" * 60)
        print("Processing completed successfully!")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\nError during processing: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_processor()
    sys.exit(0 if success else 1)