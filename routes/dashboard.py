from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from config import PRODUCT_HIERARCHY
from services import get_dataframe, filter_dataframe, validate_filters

dashboard_bp = Blueprint('dashboard', __name__)


# TAXONOMY

@dashboard_bp.route('/taxonomy', methods=['GET'])
def get_taxonomy():
    return jsonify({
        "taxonomy": PRODUCT_HIERARCHY,
        "categories": list(PRODUCT_HIERARCHY.keys())
    }), 200


# HOT TRENDS

@dashboard_bp.route('/hot_trends', methods=['GET'])
@jwt_required()
def get_hot_trends():
    try:
        df = get_dataframe().copy()

        if df.empty:
            return jsonify({
                "hot_trends": [],
                "msg": "No data available"
            }), 200

        # Group by signature (Color + Style + Product)
        trends = df.groupby(['Signature', 'Sub_Category', 'Color', 'Style']).agg({
            'Velocity_Score': 'mean',
            'text_content': 'count'
        }).reset_index()

        # Filter out unknown attributes
        trends = trends[
            (trends['Color'] != "Unknown") &
            (trends['Style'] != "Unknown")
            ]

        # Get top 4 by velocity
        top_trends = trends.sort_values('Velocity_Score', ascending=False).head(4)

        results = []
        for _, row in top_trends.iterrows():
            # Find dominant region for this trend
            trend_users = df[df['Signature'] == row['Signature']]
            region_col = 'region_clean' if 'region_clean' in df.columns else 'region'

            top_region = "Global"
            if region_col in trend_users.columns and not trend_users[region_col].empty:
                top_region = trend_users[region_col].mode()[0]

            results.append({
                "name": row['Signature'],
                "product": row['Sub_Category'],
                "score": round(row['Velocity_Score'], 1),
                "volume": int(row['text_content']),
                "top_region": top_region,
                "tags": [row['Color'], row['Style']]
            })

        return jsonify({
            "hot_trends": results,
            "total": len(results)
        }), 200

    except Exception as e:
        return jsonify({"msg": f"Error fetching hot trends: {str(e)}"}), 500


# TREND ANALYSIS

@dashboard_bp.route('/analyze', methods=['POST'])
@jwt_required()
def analyze_trends():
    try:
        filters = request.get_json() or {}

        # Validate filters
        is_valid, error_msg = validate_filters(filters)
        if not is_valid:
            return jsonify({"msg": error_msg}), 400

        # Get and filter dataframe
        df = filter_dataframe(get_dataframe().copy(), filters)

        # Apply product drilling if sub_category specified
        if filters.get('sub_category') and filters['sub_category'] != 'All':
            if 'Sub_Category' in df.columns:
                df = df[df['Sub_Category'] == filters['sub_category']]

        if df.empty:
            return jsonify({
                "error": "No data found for the given filters",
                "filters": filters
            }), 200

        # Dynamic charting based on sub_category filter
        if filters.get('sub_category') and filters['sub_category'] != 'All':
            group_col = 'Style'
            title = f"Top Styles for {filters['sub_category']}"
        else:
            group_col = 'Sub_Category'
            title = "Top Clothing Items"

        # Chart A: Velocity Leaderboard
        chart_df = df[df[group_col] != "Unknown"] if group_col in df.columns else df

        if not chart_df.empty and group_col in chart_df.columns:
            leaderboard = chart_df.groupby(group_col).agg({
                'Velocity_Score': 'mean'
            }).reset_index().sort_values('Velocity_Score', ascending=False).head(8)

            chart_a = {
                "title": title,
                "labels": leaderboard[group_col].tolist(),
                "scores": leaderboard['Velocity_Score'].round(1).tolist()
            }
        else:
            chart_a = {
                "title": title,
                "labels": [],
                "scores": []
            }

        # Chart B: Forecast Timeline
        try:
            if 'timestamp' in df.columns:
                timeline = df.groupby(df['timestamp'].dt.to_period('M')).size()
                chart_b = {
                    "title": "Trend Timeline",
                    "labels": timeline.index.astype(str).tolist(),
                    "values": timeline.values.tolist()
                }
            else:
                chart_b = {"title": "Trend Timeline", "labels": [], "values": []}
        except:
            chart_b = {"title": "Trend Timeline", "labels": [], "values": []}

        # Insights: Top Attributes
        def get_top_attributes(column, top_n=3):
            """Get top N attributes for a column"""
            if column not in df.columns:
                return ["None"]

            filtered = df[df[column] != "Unknown"][column]
            if filtered.empty:
                return ["None"]

            top = filtered.value_counts().head(top_n).index.tolist()
            return top if top else ["None"]

        insights = {
            "colors": get_top_attributes('Color'),
            "fabrics": get_top_attributes('Fabric'),
            "styles": get_top_attributes('Style')
        }

        return jsonify({
            "status": "success",
            "filters_applied": filters,
            "data_points": len(df),
            "chart_velocity": chart_a,
            "chart_forecast": chart_b,
            "insights": insights
        }), 200

    except Exception as e:
        return jsonify({"msg": f"Analysis failed: {str(e)}"}), 500


# CATEGORY BREAKDOWN

@dashboard_bp.route('/category_breakdown', methods=['GET'])
@jwt_required()
def get_category_breakdown():
    try:
        df = get_dataframe().copy()

        if df.empty:
            return jsonify({
                "categories": [],
                "msg": "No data available"
            }), 200

        if 'Sub_Category' not in df.columns:
            return jsonify({
                "categories": [],
                "msg": "Category data not available"
            }), 200

        # Group by category
        breakdown = df.groupby('Sub_Category').agg({
            'Velocity_Score': 'mean',
            'text_content': 'count'
        }).reset_index()

        breakdown = breakdown.sort_values('Velocity_Score', ascending=False)

        results = []
        for _, row in breakdown.iterrows():
            results.append({
                "category": row['Sub_Category'],
                "velocity": round(row['Velocity_Score'], 1),
                "volume": int(row['text_content'])
            })

        return jsonify({
            "categories": results,
            "total": len(results)
        }), 200

    except Exception as e:
        return jsonify({"msg": f"Error getting category breakdown: {str(e)}"}), 500


# SEARCH

@dashboard_bp.route('/search', methods=['GET'])
@jwt_required()
def search_trends():
    try:
        query = request.args.get('q', '').strip().lower()

        if not query:
            return jsonify({"msg": "Search query required"}), 400

        df = get_dataframe().copy()

        if df.empty:
            return jsonify({"results": []}), 200

        # Search in signature, product, color, style
        search_cols = ['Signature', 'Sub_Category', 'Color', 'Style']
        mask = None

        for col in search_cols:
            if col in df.columns:
                col_mask = df[col].str.lower().str.contains(query, na=False)
                mask = col_mask if mask is None else (mask | col_mask)

        if mask is None:
            return jsonify({"results": []}), 200

        results_df = df[mask]

        # Group by signature
        grouped = results_df.groupby('Signature').agg({
            'Velocity_Score': 'mean',
            'text_content': 'count'
        }).reset_index().sort_values('Velocity_Score', ascending=False).head(10)

        results = []
        for _, row in grouped.iterrows():
            item_data = results_df[results_df['Signature'] == row['Signature']].iloc[0]
            results.append({
                "name": row['Signature'],
                "product": item_data.get('Sub_Category', 'Unknown'),
                "color": item_data.get('Color', 'Unknown'),
                "style": item_data.get('Style', 'Unknown'),
                "velocity": round(row['Velocity_Score'], 1),
                "volume": int(row['text_content'])
            })

        return jsonify({
            "query": query,
            "results": results,
            "total": len(results)
        }), 200

    except Exception as e:
        return jsonify({"msg": f"Search failed: {str(e)}"}), 500


# FILTERS INFO

@dashboard_bp.route('/available_filters', methods=['GET'])
@jwt_required()
def get_available_filters():
    try:
        df = get_dataframe().copy()

        if df.empty:
            return jsonify({
                "regions": [],
                "seasons": [],
                "categories": [],
                "msg": "No data available"
            }), 200

        filters = {
            "regions": sorted(df['region'].unique().tolist()) if 'region' in df.columns else [],
            "seasons": sorted(df['Season'].unique().tolist()) if 'Season' in df.columns else [],
            "categories": sorted(df['Sub_Category'].unique().tolist()) if 'Sub_Category' in df.columns else [],
            "genders": ["All", "Male", "Female"],
            "age_groups": ["All", "18-24", "25-34", "35-44", "45-54", "55+"]
        }

        return jsonify(filters), 200

    except Exception as e:
        return jsonify({"msg": f"Error getting filters: {str(e)}"}), 500