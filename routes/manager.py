from flask import Blueprint, request, jsonify
# ADD get_jwt to imports
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from extensions import db
from models import PredictionBatch, PredictionItem
from services import analyze_trends_logic, validate_filters
from config import ROLES
from functools import wraps
import uuid

manager_bp = Blueprint('manager', __name__)

def manager_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        claims = get_jwt()
        user_role = claims.get('role')

        if user_role not in [ROLES['MANAGER'], ROLES['ADMIN']]:
            return jsonify({"msg": "Manager access required"}), 403

        return fn(*args, **kwargs)

    return wrapper


# PREDICTION GENERATION
@manager_bp.route('/generate_prediction', methods=['POST'])
@jwt_required()
@manager_required
def generate_and_store():
    try:
        current_user_id = get_jwt_identity()
        filters = request.get_json() or {}

        # Validate filters
        is_valid, error_msg = validate_filters(filters)
        if not is_valid:
            return jsonify({"msg": error_msg}), 400

        # Run the trend analysis algorithm
        prediction_results = analyze_trends_logic(filters)

        if not prediction_results:
            return jsonify({
                "msg": "No data found for the given parameters",
                "filters": filters
            }), 404

        # Generate unique batch ID
        batch_id = f"PRED-{uuid.uuid4().hex[:8].upper()}"

        # Create prediction batch (T1)
        new_batch = PredictionBatch(
            uni_id=batch_id,
            created_by=int(current_user_id),  # Convert string ID to int
            region=filters.get('region', 'All'),
            season=filters.get('season', 'All'),
            gender=filters.get('gender', 'All'),
            age_group=filters.get('age_group', 'All')
        )

        db.session.add(new_batch)

        # Create prediction items (T2)
        items_created = []
        for item in prediction_results:
            new_item = PredictionItem(
                uni_id=batch_id,
                product=item['product'],
                color=item['color'],
                fabric=item['fabric'],
                style=item['style'],
                status='pending'
            )
            db.session.add(new_item)
            items_created.append(new_item.to_dict())

        db.session.commit()

        return jsonify({
            "msg": "Prediction generated and stored successfully",
            "batch_id": batch_id,
            "items_count": len(prediction_results),
            "filters": filters,
            "items": items_created
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Prediction generation failed: {str(e)}"}), 500


# PREDICTION MANAGEMENT
@manager_bp.route('/predictions', methods=['GET'])
@jwt_required()
@manager_required
def get_predictions():
    try:
        current_user_id = int(get_jwt_identity())
        claims = get_jwt()
        user_role = claims.get('role')

        # Build query - managers see only their predictions, admins see all
        if user_role == ROLES['MANAGER']:
            query = PredictionBatch.query.filter_by(created_by=current_user_id)
        else:
            query = PredictionBatch.query

        # Apply status filter if provided
        status_filter = request.args.get('status')
        if status_filter:
            query = query.join(PredictionItem).filter(
                PredictionItem.status == status_filter
            ).distinct()

        # Order by creation date (newest first)
        batches = query.order_by(PredictionBatch.created_at.desc()).all()

        return jsonify({
            "predictions": [batch.to_dict(include_items=True) for batch in batches],
            "total": len(batches)
        }), 200

    except Exception as e:
        return jsonify({"msg": f"Error fetching predictions: {str(e)}"}), 500


@manager_bp.route('/predictions/<batch_id>', methods=['GET'])
@jwt_required()
@manager_required
def get_prediction_details(batch_id):
    try:
        current_user_id = int(get_jwt_identity())
        claims = get_jwt()
        user_role = claims.get('role')

        batch = PredictionBatch.query.get(batch_id)

        if not batch:
            return jsonify({"msg": "Prediction batch not found"}), 404

        # Managers can only see their own predictions
        if user_role == ROLES['MANAGER'] and batch.created_by != current_user_id:
            return jsonify({"msg": "Access denied"}), 403

        return jsonify(batch.to_dict(include_items=True)), 200

    except Exception as e:
        return jsonify({"msg": f"Error fetching prediction details: {str(e)}"}), 500


@manager_bp.route('/predictions/<batch_id>', methods=['DELETE'])
@jwt_required()
@manager_required
def delete_prediction(batch_id):
    try:
        current_user_id = int(get_jwt_identity())
        claims = get_jwt()
        user_role = claims.get('role')

        batch = PredictionBatch.query.get(batch_id)

        if not batch:
            return jsonify({"msg": "Prediction batch not found"}), 404

        # Managers can only delete their own predictions
        if user_role == ROLES['MANAGER'] and batch.created_by != current_user_id:
            return jsonify({"msg": "Access denied"}), 403

        # Check if any items are already approved/rejected
        non_pending = [item for item in batch.items if item.status != 'pending']
        if non_pending:
            return jsonify({
                "msg": "Cannot delete batch with approved/rejected items",
                "non_pending_count": len(non_pending)
            }), 400

        db.session.delete(batch)
        db.session.commit()

        return jsonify({
            "msg": f"Prediction batch '{batch_id}' deleted successfully"
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Error deleting prediction: {str(e)}"}), 500


# STATISTICS
@manager_bp.route('/stats', methods=['GET'])
@jwt_required()
@manager_required
def get_manager_stats():
    try:
        current_user_id = int(get_jwt_identity())
        claims = get_jwt()
        user_role = claims.get('role')

        # Base query
        if user_role == ROLES['MANAGER']:
            batch_query = PredictionBatch.query.filter_by(created_by=current_user_id)
        else:
            batch_query = PredictionBatch.query

        batches = batch_query.all()

        # Count items by status
        all_items = []
        for batch in batches:
            all_items.extend(batch.items)

        pending = sum(1 for item in all_items if item.status == 'pending')
        approved = sum(1 for item in all_items if item.status == 'approved')
        rejected = sum(1 for item in all_items if item.status == 'rejected')

        stats = {
            "total_batches": len(batches),
            "total_items": len(all_items),
            "items_by_status": {
                "pending": pending,
                "approved": approved,
                "rejected": rejected
            },
            "approval_rate": round((approved / len(all_items) * 100), 1) if all_items else 0
        }

        return jsonify(stats), 200

    except Exception as e:
        return jsonify({"msg": f"Error getting stats: {str(e)}"}), 500


# PREVIEW (Without Saving)
@manager_bp.route('/preview_prediction', methods=['POST'])
@jwt_required()
@manager_required
def preview_prediction():
    try:
        filters = request.get_json() or {}

        is_valid, error_msg = validate_filters(filters)
        if not is_valid:
            return jsonify({"msg": error_msg}), 400

        prediction_results = analyze_trends_logic(filters)

        if not prediction_results:
            return jsonify({
                "msg": "No data found for the given parameters",
                "filters": filters,
                "results": []
            }), 200

        return jsonify({
            "msg": "Preview generated successfully",
            "filters": filters,
            "results": prediction_results,
            "count": len(prediction_results)
        }), 200

    except Exception as e:
        return jsonify({"msg": f"Preview failed: {str(e)}"}), 500