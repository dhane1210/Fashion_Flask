import pandas as pd
import numpy as np
import os
import re
from config import PATHS, TAXONOMY, ATTRIBUTES

def clean_text_simple(text):
    return str(text).lower()

def extract_category(text):
    text = clean_text_simple(text)
    
    # We only have "Clothing" now, so we loop through its sub-categories
    clothing_rules = TAXONOMY["Clothing"]["sub_categories"]
    
    for sub_cat, keywords in clothing_rules.items():
        for keyword in keywords:
            # Add spaces to ensure we don't match partial words (e.g. 'top' inside 'stop')
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
    """Simulates SS26/FW26 based on month"""
    try:
        dt = pd.to_datetime(row['timestamp'])
        if 4 <= dt.month <= 8: return "SS26"
        else: return "FW26"
    except: return "Core/Evergreen"

def run_processor():
    print("🚀 Starting SIMPLIFIED Data Processor...")
    
    if not os.path.exists(PATHS['raw_csv']):
        print(f"❌ Error: {PATHS['raw_csv']} not found.")
        return

    # 1. Load
    df = pd.read_csv(PATHS['raw_csv'])
    print(f"✅ Loaded {len(df)} rows.")

    # 2. Tag Products (Strict Filtering)
    print("... Filtering for Clothing Only")
    tag_results = df['text_content'].apply(extract_category)
    df['Category'] = [x[0] for x in tag_results]
    df['Sub_Category'] = [x[1] for x in tag_results]

    # DROP anything that isn't Clothing
    df = df[df['Category'] == "Clothing"].copy()
    print(f"✅ Filtered to {len(df)} Clothing items.")

    # 3. Extract Attributes
    print("... Extracting Attributes")
    attr_results = df['text_content'].apply(extract_attributes)
    df['Color'] = [x['Color'] for x in attr_results]
    df['Fabric'] = [x['Fabric'] for x in attr_results]
    df['Style'] = [x['Style'] for x in attr_results]

    # 4. Assign Season
    df['Season'] = df.apply(assign_season, axis=1)

    # 5. Calculate Velocity (Randomized for Demo)
    print("... Calculating Velocity")
    # Base popularity on count
    pop_score = df.groupby('Sub_Category')['text_content'].transform('count')
    random_growth = np.random.randint(-10, 80, size=len(df))
    
    # Normalize 0-100
    df['Velocity_Score'] = ((pop_score + random_growth) / (pop_score.max() + 100)) * 100
    df['Velocity_Score'] = df['Velocity_Score'].clip(10, 99).round(1)

    # 6. Save
    df.to_csv(PATHS['processed_csv'], index=False)
    print(f"🎉 Success! Saved to: {PATHS['processed_csv']}")
    print(df['Sub_Category'].value_counts())

if __name__ == "__main__":
    run_processor()