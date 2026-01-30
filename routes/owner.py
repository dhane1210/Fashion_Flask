from flask import Blueprint, request, jsonify
# ADD get_jwt to imports
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from extensions import db
from models import PredictionItem, PredictionBatch, User
from config import ROLES, PREDICTION_STATUS
from functools import wraps
from datetime import datetime

owner_bp = Blueprint('owner', __name__)

def owner_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        claims = get_jwt()
        if claims.get('role') not in [ROLES['OWNER'], ROLES['ADMIN']]:
            return jsonify({"msg": "Owner access required"}), 403

        return fn(*args, **kwargs)

    return wrapper


# PENDING ITEMS

@owner_bp.route('/pending_items', methods=['GET'])
@jwt_required()
@owner_required
def get_pending():
    try:
        # join items with batches for context
        query = db.session.query(PredictionItem, PredictionBatch).join(
            PredictionBatch,
            PredictionItem.uni_id == PredictionBatch.uni_id
        ).filter(PredictionItem.status == PREDICTION_STATUS['PENDING'])

        # Filter by batch if specified
        batch_id = request.args.get('batch_id')
        if batch_id:
            query = query.filter(PredictionItem.uni_id == batch_id)

        # Order by creation date (oldest first for review queue)
        query = query.order_by(PredictionBatch.created_at.asc())

        results = query.all()

        output = []
        for item, batch in results:
            # Get creator info
            creator = User.query.get(batch.created_by)

            output.append({
                "item_id": item.id,
                "batch_id": batch.uni_id,
                "product": item.product,
                "color": item.color,
                "fabric": item.fabric,
                "style": item.style,
                "status": item.status,
                "context": {
                    "season": batch.season,
                    "region": batch.region,
                    "gender": batch.gender,
                    "age_group": batch.age_group
                },
                "created_by": creator.username if creator else "Unknown",
                "created_at": batch.created_at.isoformat() if batch.created_at else None
            })

        return jsonify({
            "pending_items": output,
            "total": len(output)
        }), 200

    except Exception as e:
        return jsonify({"msg": f"Error fetching pending items: {str(e)}"}), 500


@owner_bp.route('/pending_batches', methods=['GET'])
@jwt_required()
@owner_required
def get_pending_batches():
    try:
        # Find all batches with at least one pending item
        batches_with_pending = db.session.query(PredictionBatch).join(
            PredictionItem
        ).filter(
            PredictionItem.status == PREDICTION_STATUS['PENDING']
        ).distinct().order_by(PredictionBatch.created_at.asc()).all()

        output = []
        for batch in batches_with_pending:
            pending_count = sum(1 for item in batch.items if item.status == 'pending')
            creator = User.query.get(batch.created_by)

            output.append({
                "batch_id": batch.uni_id,
                "created_by": creator.username if creator else "Unknown",
                "created_at": batch.created_at.isoformat() if batch.created_at else None,
                "parameters": {
                    "region": batch.region,
                    "season": batch.season,
                    "gender": batch.gender,
                    "age_group": batch.age_group
                },
                "pending_count": pending_count,
                "total_items": len(batch.items)
            })

        return jsonify({
            "pending_batches": output,
            "total": len(output)
        }), 200

    except Exception as e:
        return jsonify({"msg": f"Error fetching pending batches: {str(e)}"}), 500


# APPROVAL / REJECTION

@owner_bp.route('/update_status', methods=['POST'])
@jwt_required()
@owner_required
def update_status():
    try:
        current_user_id = int(get_jwt_identity())
        data = request.get_json()

        # Validation
        if not data or 'item_id' not in data or 'action' not in data:
            return jsonify({"msg": "item_id and action are required"}), 400

        if data['action'] not in ['approve', 'reject']:
            return jsonify({"msg": "action must be 'approve' or 'reject'"}), 400

        # Get item
        item = PredictionItem.query.get(data['item_id'])

        if not item:
            return jsonify({"msg": "Prediction item not found"}), 404

        # Check if already reviewed
        if item.status != PREDICTION_STATUS['PENDING']:
            return jsonify({
                "msg": f"Item already {item.status}",
                "current_status": item.status
            }), 400

        # Update status
        if data['action'] == 'approve':
            item.status = PREDICTION_STATUS['APPROVED']
        elif data['action'] == 'reject':
            item.status = PREDICTION_STATUS['REJECTED']

        item.reviewed_at = datetime.utcnow()
        # FIX: Assign ID directly
        item.reviewed_by = current_user_id

        db.session.commit()

        return jsonify({
            "msg": f"Item {item.status} successfully",
            "item": item.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Status update failed: {str(e)}"}), 500


@owner_bp.route('/batch_update_status', methods=['POST'])
@jwt_required()
@owner_required
def batch_update_status():
    try:
        current_user_id = int(get_jwt_identity())
        data = request.get_json()

        # Validation
        if not data or 'item_ids' not in data or 'action' not in data:
            return jsonify({"msg": "item_ids and action are required"}), 400

        if data['action'] not in ['approve', 'reject']:
            return jsonify({"msg": "action must be 'approve' or 'reject'"}), 400

        if not isinstance(data['item_ids'], list):
            return jsonify({"msg": "item_ids must be a list"}), 400

        # Process each item
        updated = []
        errors = []

        for item_id in data['item_ids']:
            try:
                item = PredictionItem.query.get(item_id)

                if not item:
                    errors.append(f"Item {item_id} not found")
                    continue

                if item.status != PREDICTION_STATUS['PENDING']:
                    errors.append(f"Item {item_id} already {item.status}")
                    continue

                # Update status
                if data['action'] == 'approve':
                    item.status = PREDICTION_STATUS['APPROVED']
                elif data['action'] == 'reject':
                    item.status = PREDICTION_STATUS['REJECTED']

                item.reviewed_at = datetime.utcnow()
                # FIX: Assign ID directly
                item.reviewed_by = current_user_id

                updated.append(item_id)

            except Exception as e:
                errors.append(f"Item {item_id}: {str(e)}")

        db.session.commit()

        return jsonify({
            "msg": f"{len(updated)} items updated successfully",
            "updated": updated,
            "errors": errors if errors else None
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Batch update failed: {str(e)}"}), 500


@owner_bp.route('/approve_batch/<batch_id>', methods=['POST'])
@jwt_required()
@owner_required
def approve_entire_batch(batch_id):
    try:
        current_user_id = int(get_jwt_identity())

        batch = PredictionBatch.query.get(batch_id)

        if not batch:
            return jsonify({"msg": "Batch not found"}), 404

        # Get all pending items in this batch
        pending_items = [item for item in batch.items if item.status == PREDICTION_STATUS['PENDING']]

        if not pending_items:
            return jsonify({"msg": "No pending items in this batch"}), 400

        # Approve all
        for item in pending_items:
            item.status = PREDICTION_STATUS['APPROVED']
            item.reviewed_at = datetime.utcnow()
            # FIX: Assign ID directly
            item.reviewed_by = current_user_id

        db.session.commit()

        return jsonify({
            "msg": f"All {len(pending_items)} pending items in batch approved",
            "batch_id": batch_id,
            "items_approved": len(pending_items)
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Batch approval failed: {str(e)}"}), 500


# REVIEW HISTORY
@owner_bp.route('/review_history', methods=['GET'])
@jwt_required()
@owner_required
def get_review_history():
    try:
        # Query reviewed items (not pending)
        query = db.session.query(PredictionItem, PredictionBatch).join(
            PredictionBatch
        ).filter(
            PredictionItem.status != PREDICTION_STATUS['PENDING']
        )

        # Filter by status if provided
        status_filter = request.args.get('status')
        if status_filter in [PREDICTION_STATUS['APPROVED'], PREDICTION_STATUS['REJECTED']]:
            query = query.filter(PredictionItem.status == status_filter)

        # Order by review date (newest first)
        query = query.order_by(PredictionItem.reviewed_at.desc())

        results = query.all()

        output = []
        for item, batch in results:
            reviewer = User.query.get(item.reviewed_by) if item.reviewed_by else None
            creator = User.query.get(batch.created_by)

            output.append({
                "item_id": item.id,
                "batch_id": batch.uni_id,
                "product": item.product,
                "color": item.color,
                "fabric": item.fabric,
                "style": item.style,
                "status": item.status,
                "reviewed_at": item.reviewed_at.isoformat() if item.reviewed_at else None,
                "reviewed_by": reviewer.username if reviewer else "Unknown",
                "created_by": creator.username if creator else "Unknown",
                "context": {
                    "season": batch.season,
                    "region": batch.region
                }
            })

        return jsonify({
            "review_history": output,
            "total": len(output)
        }), 200

    except Exception as e:
        return jsonify({"msg": f"Error fetching review history: {str(e)}"}), 500


# STATISTICS

@owner_bp.route('/stats', methods=['GET'])
@jwt_required()
@owner_required
def get_owner_stats():
    try:
        all_items = PredictionItem.query.all()

        pending = sum(1 for item in all_items if item.status == PREDICTION_STATUS['PENDING'])
        approved = sum(1 for item in all_items if item.status == PREDICTION_STATUS['APPROVED'])
        rejected = sum(1 for item in all_items if item.status == PREDICTION_STATUS['REJECTED'])

        stats = {
            "total_items": len(all_items),
            "items_by_status": {
                "pending": pending,
                "approved": approved,
                "rejected": rejected
            },
            "approval_rate": round((approved / len(all_items) * 100), 1) if all_items else 0,
            "rejection_rate": round((rejected / len(all_items) * 100), 1) if all_items else 0
        }

        return jsonify(stats), 200

    except Exception as e:
        return jsonify({"msg": f"Error getting stats: {str(e)}"}), 500