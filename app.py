import pandas as pd
from flask import Flask, request, jsonify
from flask_cors import CORS
from config import PATHS, PRODUCT_HIERARCHY
import os

app = Flask(__name__)
CORS(app)

# Load Data
DF_MAIN = pd.DataFrame()

def load_data():
    global DF_MAIN
    if os.path.exists(PATHS['processed_csv']):
        DF_MAIN = pd.read_csv(PATHS['processed_csv'])
        DF_MAIN['timestamp'] = pd.to_datetime(DF_MAIN['timestamp'], errors='coerce')
        DF_MAIN['Signature'] = DF_MAIN['Color'] + " " + DF_MAIN['Style'] + " " + DF_MAIN['Sub_Category']
        print(f"✅ Loaded {len(DF_MAIN)} rows.")
    else:
        print("❌ Error: Processed CSV not found.")

load_data()

# --- HELPER: FILTERING LOGIC ---
def filter_dataframe(filters):
    df = DF_MAIN.copy()
    
    # 1. Region
    if filters.get('region') and filters['region'] != 'All':
        col = 'region_clean' if 'region_clean' in df.columns else 'region'
        df = df[df[col] == filters['region']]
        
    # 2. Season
    if filters.get('season') and filters['season'] != 'All':
        df = df[df['Season'] == filters['season']]
        
    # 3. Gender
    if filters.get('gender') and filters['gender'] != 'All':
        df = df[df['gender'].str.upper() == filters['gender'].upper()]

    # 4. Age Group (New)
    if filters.get('age_group') and filters['age_group'] != 'All':
        age_map = {
            "18-24": (18, 24), "25-34": (25, 34),
            "35-44": (35, 44), "45-54": (45, 54), "55+": (55, 100)
        }
        if filters['age_group'] in age_map:
            min_a, max_a = age_map[filters['age_group']]
            df = df[(df['age'] >= min_a) & (df['age'] <= max_a)]

    return df

# --- ENDPOINTS ---

@app.route('/', methods=['GET'])
def home(): return jsonify({"status": "Online"})

@app.route('/api/taxonomy', methods=['GET'])
def get_taxonomy(): return jsonify(PRODUCT_HIERARCHY)

@app.route('/api/hot_trends', methods=['GET'])
def get_hot_trends():
    df = DF_MAIN.copy()
    trends = df.groupby(['Signature', 'Sub_Category', 'Color', 'Style']).agg({
        'Velocity_Score': 'mean', 'text_content': 'count'
    }).reset_index()
    trends = trends[(trends['Color'] != "Unknown") & (trends['Style'] != "Unknown")]
    top_trends = trends.sort_values('Velocity_Score', ascending=False).head(4)
    
    results = []
    for _, row in top_trends.iterrows():
        trend_users = df[df['Signature'] == row['Signature']]
        reg_col = 'region_clean' if 'region_clean' in df.columns else 'region'
        top_region = trend_users[reg_col].mode()[0] if reg_col in trend_users else "Global"
        results.append({
            "name": row['Signature'], "score": round(row['Velocity_Score'], 1),
            "volume": int(row['text_content']), "top_region": top_region,
            "tags": [row['Color'], row['Style']]
        })
    return jsonify(results)

@app.route('/api/analyze', methods=['POST'])
def analyze_trends():
    filters = request.json or {}
    df = filter_dataframe(filters)
    
    if df.empty: return jsonify({"error": "No data found"}), 200

    # --- 1. OVERVIEW: Show ALL Categories ---
    # We always group by 'Sub_Category' to show the full leaderboard
    leaderboard = df.groupby('Sub_Category').agg({
        'Velocity_Score': 'mean'
    }).reset_index().sort_values('Velocity_Score', ascending=False)

    chart_a = {
        "title": "Category Velocity Leaderboard",
        "labels": leaderboard['Sub_Category'].tolist(),
        "scores": leaderboard['Velocity_Score'].round(1).tolist()
    }

    # --- 2. DRILL DOWN LOGIC ---
    # If the user clicked a specific category, we filter for that to get details.
    # If not, we pick the #1 top category as default.
    selected_category = filters.get('selected_category') 
    if not selected_category or selected_category == "All":
        selected_category = leaderboard.iloc[0]['Sub_Category'] # Default to winner
    
    # Filter dataset specifically for the Insights & Forecast
    detail_df = df[df['Sub_Category'] == selected_category]

    # Chart B: Forecast for Selected Category
    try:
        timeline = detail_df.groupby(detail_df['timestamp'].dt.to_period('M')).size()
        chart_b = {"labels": timeline.index.astype(str).tolist(), "values": timeline.values.tolist()}
    except: chart_b = {"labels": [], "values": []}

    # Insights: Attributes for Selected Category
    def get_top(col):
        if col not in detail_df.columns: return ["None"]
        v = detail_df[detail_df[col] != "Unknown"][col].value_counts().head(3).index.tolist()
        return v if v else ["None"]

    return jsonify({
        "status": "success",
        "selected_focus": selected_category, # Tell UI what we are looking at
        "chart_velocity": chart_a,
        "chart_forecast": chart_b,
        "insights": {
            "colors": get_top('Color'),
            "fabrics": get_top('Fabric'),
            "styles": get_top('Style')
        }
    })

if __name__ == '__main__':
    app.run(port=5001, debug=True)