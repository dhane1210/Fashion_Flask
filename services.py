import pandas as pd
import os
from config import PATHS, AGE_GROUPS

# Global storage for the dataframe (in-memory cache)
_DF_MAIN = pd.DataFrame()


def load_data_into_memory():
    global _DF_MAIN

    try:
        if not os.path.exists(PATHS['processed_csv']):
            print(f"Warning: Processed CSV not found at {PATHS['processed_csv']}")
            return False

        df = pd.read_csv(PATHS['processed_csv'])

        # Data preprocessing
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')

        # Create signature for trend identification
        df['Signature'] = df['Color'] + " " + df['Style'] + " " + df['Sub_Category']

        _DF_MAIN = df
        print(f"Service: Data loaded successfully ({len(df)} rows)")
        return True

    except Exception as e:
        print(f"Error loading data: {str(e)}")
        return False


def get_dataframe():
    if _DF_MAIN.empty:
        load_data_into_memory()
    return _DF_MAIN


def reload_data():
    global _DF_MAIN
    _DF_MAIN = pd.DataFrame()
    return load_data_into_memory()


def filter_dataframe(df, filters):
    df = df.copy()

    # Region filter
    if filters.get('region') and filters['region'] != 'All':
        col = 'region_clean' if 'region_clean' in df.columns else 'region'
        if col in df.columns:
            df = df[df[col] == filters['region']]

    # Season filter
    if filters.get('season') and filters['season'] != 'All':
        if 'Season' in df.columns:
            df = df[df['Season'] == filters['season']]

    # Gender filter
    if filters.get('gender') and filters['gender'] != 'All':
        if 'gender' in df.columns:
            df = df[df['gender'].str.upper() == filters['gender'].upper()]

    # Age Group filter
    if filters.get('age_group') and filters['age_group'] != 'All':
        if filters['age_group'] in AGE_GROUPS and 'age' in df.columns:
            min_age, max_age = AGE_GROUPS[filters['age_group']]
            df = df[(df['age'] >= min_age) & (df['age'] <= max_age)]

    return df


def analyze_trends_logic(filters):
    df = get_dataframe().copy()

    if df.empty:
        return None

    # 1. Apply User Filters
    df = filter_dataframe(df, filters)

    if df.empty:
        return None

    # 2. Find Top 5 Products (Sub_Categories) by Volume
    # We group by Product Name first, not the full signature
    top_products = df['Sub_Category'].value_counts().head(5).index.tolist()

    results = []
    for product in top_products:
        # Get all rows for this specific product (e.g., all "Dresses")
        product_df = df[df['Sub_Category'] == product]

        # --- SMART ATTRIBUTE FINDER ---
        # This function finds the most common value that ISN'T "Unknown"
        def get_best_attribute(column_name):
            # Filter out unknowns
            valid_values = product_df[product_df[column_name] != "Unknown"][column_name]
            
            if valid_values.empty:
                return "Various" # Better UI than "Unknown"
            
            # Return the most frequent valid value
            return valid_values.value_counts().idxmax()

        # Build the result
        results.append({
            "product": product,
            "color": get_best_attribute('Color'),
            "fabric": get_best_attribute('Fabric'),
            "style": get_best_attribute('Style'),
            "velocity_score": round(product_df['Velocity_Score'].mean(), 1)
        })

    return results



def get_data_summary():
    df = get_dataframe()

    if df.empty:
        return {
            "loaded": False,
            "total_rows": 0
        }

    summary = {
        "loaded": True,
        "total_rows": len(df),
        "date_range": {
            "start": df['timestamp'].min().isoformat() if 'timestamp' in df.columns else None,
            "end": df['timestamp'].max().isoformat() if 'timestamp' in df.columns else None
        },
        "categories": df['Sub_Category'].unique().tolist() if 'Sub_Category' in df.columns else [],
        "regions": df['region'].unique().tolist() if 'region' in df.columns else []
    }

    return summary


def validate_filters(filters):
    valid_seasons = ['All', 'SS26', 'FW26', 'Core/Evergreen']
    valid_genders = ['All', 'M', 'F', 'MALE', 'FEMALE']
    valid_age_groups = ['All'] + list(AGE_GROUPS.keys())

    # Validate season
    if filters.get('season') and filters['season'] not in valid_seasons:
        return False, f"Invalid season. Must be one of: {', '.join(valid_seasons)}"

    # Validate gender
    if filters.get('gender') and filters['gender'].upper() not in valid_genders:
        return False, f"Invalid gender. Must be one of: {', '.join(valid_genders)}"

    # Validate age group
    if filters.get('age_group') and filters['age_group'] not in valid_age_groups:
        return False, f"Invalid age group. Must be one of: {', '.join(valid_age_groups)}"

    return True, None