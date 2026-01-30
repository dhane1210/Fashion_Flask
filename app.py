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
        # Signature for Hot Trends
        DF_MAIN['Signature'] = DF_MAIN['Color'] + " " + DF_MAIN['Style'] + " " + DF_MAIN['Sub_Category']
        print(f"✅ Loaded {len(DF_MAIN)} rows.")
    else:
        print("❌ Error: Processed CSV not found. Run data_processor.py")

load_data()

# --- ROUTES ---

@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "Online", "mode": "Clothing-Only"})

@app.route('/api/taxonomy', methods=['GET'])
def get_taxonomy():
    return jsonify(PRODUCT_HIERARCHY)

@app.route('/api/hot_trends', methods=['GET'])
def get_hot_trends():
    df = DF_MAIN.copy()
    # Find combinations (e.g. Red Oversized Hoodie)
    trends = df.groupby(['Signature', 'Sub_Category', 'Color', 'Style']).agg({
        'Velocity_Score': 'mean', 'text_content': 'count'
    }).reset_index()
    
    # Filter out Unknowns
    trends = trends[trends['Color'] != "Unknown"]
    trends = trends[trends['Style'] != "Unknown"]
    
    # Get top 4 highest velocity
    top_trends = trends.sort_values('Velocity_Score', ascending=False).head(4)
    
    results = []
    for _, row in top_trends.iterrows():
        # Find dominant region for this item
        trend_users = df[df['Signature'] == row['Signature']]
        region_col = 'region_clean' if 'region_clean' in df.columns else 'region'
        top_region = trend_users[region_col].mode()[0] if region_col in trend_users else "Global"

        results.append({
            "name": row['Signature'],
            "score": round(row['Velocity_Score'], 1),
            "volume": int(row['text_content']),
            "top_region": top_region,
            "tags": [row['Color'], row['Style']]
        })
    return jsonify(results)

@app.route('/api/analyze', methods=['POST'])
def analyze_trends():
    filters = request.json or {}
    df = DF_MAIN.copy()
    
    # Filters
    if filters.get('region') and filters['region'] != 'All':
        col = 'region_clean' if 'region_clean' in df.columns else 'region'
        df = df[df[col] == filters['region']]
    if filters.get('season') and filters['season'] != 'All':
        df = df[df['Season'] == filters['season']]
    if filters.get('gender') and filters['gender'] != 'All':
        df = df[df['gender'].str.upper() == filters['gender'].upper()]
    
    # Product Drilling
    if filters.get('sub_category') and filters['sub_category'] != 'All':
        df = df[df['Sub_Category'] == filters['sub_category']]

    if df.empty: return jsonify({"error": "No data found"}), 200

    # Dynamic Charting
    # If a specific product is selected, breakdown by Style. Otherwise by Product.
    if filters.get('sub_category') and filters['sub_category'] != 'All':
        group_col = 'Style'
        title = f"Top Styles for {filters['sub_category']}"
    else:
        group_col = 'Sub_Category'
        title = "Top Clothing Items"

    # Chart A (Velocity)
    chart_df = df[df[group_col] != "Unknown"]
    leaderboard = chart_df.groupby(group_col).agg({
        'Velocity_Score': 'mean'
    }).reset_index().sort_values('Velocity_Score', ascending=False).head(8)

    chart_a = {
        "title": title,
        "labels": leaderboard[group_col].tolist(),
        "scores": leaderboard['Velocity_Score'].round(1).tolist()
    }

    # Chart B (Forecast)
    try:
        timeline = df.groupby(df['timestamp'].dt.to_period('M')).size()
        chart_b = {"labels": timeline.index.astype(str).tolist(), "values": timeline.values.tolist()}
    except: chart_b = {"labels": [], "values": []}

    # Insights
    def get_top(col):
        v = df[df[col] != "Unknown"][col].value_counts().head(3).index.tolist()
        return v if v else ["None"]

    return jsonify({
        "status": "success",
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