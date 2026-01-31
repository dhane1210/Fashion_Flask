from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from extensions import db, bcrypt
from models import User
from config import PATHS, ROLES
from services import reload_data, get_data_summary
from data_processor import run_processor
from functools import wraps
import os

admin_bp = Blueprint('admin', __name__)


def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        claims = get_jwt()
        if claims.get('role') != ROLES['ADMIN']:
            return jsonify({"msg": "Admins only!"}), 403

        return fn(*args, **kwargs)

    return wrapper


# USER MANAGEMENT

@admin_bp.route('/users', methods=['GET'])
@jwt_required()
@admin_required
def get_users():
    try:
        role_filter = request.args.get('role')

        if role_filter:
            users = User.query.filter_by(role=role_filter).all()
        else:
            users = User.query.all()

        return jsonify({
            "users": [user.to_dict() for user in users],
            "total": len(users)
        }), 200

    except Exception as e:
        return jsonify({"msg": f"Error fetching users: {str(e)}"}), 500


@admin_bp.route('/users/<int:user_id>', methods=['GET'])
@jwt_required()
@admin_required
def get_user(user_id):
    try:
        user = User.query.get(user_id)

        if not user:
            return jsonify({"msg": "User not found"}), 404

        return jsonify(user.to_dict()), 200

    except Exception as e:
        return jsonify({"msg": f"Error fetching user: {str(e)}"}), 500


@admin_bp.route('/users', methods=['POST'])
@jwt_required()
@admin_required
def create_user():
    try:
        data = request.get_json()

        # Validation
        required_fields = ['username', 'password', 'role']
        for field in required_fields:
            if field not in data:
                return jsonify({"msg": f"Missing required field: {field}"}), 400

        # Validate role
        valid_roles = [ROLES['ADMIN'], ROLES['MANAGER'], ROLES['OWNER']]
        if data['role'] not in valid_roles:
            return jsonify({"msg": f"Invalid role. Must be one of: {', '.join(valid_roles)}"}), 400

        # Check if username exists
        if User.query.filter_by(username=data['username']).first():
            return jsonify({"msg": "Username already exists"}), 409

        # Create user
        hashed_pw = bcrypt.generate_password_hash(data['password']).decode('utf-8')
        new_user = User(
            username=data['username'],
            password_hash=hashed_pw,
            role=data['role']
        )

        db.session.add(new_user)
        db.session.commit()

        return jsonify({
            "msg": "User created successfully",
            "user": new_user.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Error creating user: {str(e)}"}), 500


@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@jwt_required()
@admin_required
def update_user(user_id):
    try:
        user = User.query.get(user_id)

        if not user:
            return jsonify({"msg": "User not found"}), 404

        data = request.get_json()

        # Update role if provided
        if 'role' in data:
            valid_roles = [ROLES['ADMIN'], ROLES['MANAGER'], ROLES['OWNER']]
            if data['role'] not in valid_roles:
                return jsonify({"msg": f"Invalid role. Must be one of: {', '.join(valid_roles)}"}), 400
            user.role = data['role']

        # Update active status if provided
        if 'is_active' in data:
            user.is_active = bool(data['is_active'])

        # Update password if provided
        if 'password' in data:
            if len(data['password']) < 6:
                return jsonify({"msg": "Password must be at least 6 characters"}), 400
            user.password_hash = bcrypt.generate_password_hash(data['password']).decode('utf-8')

        db.session.commit()

        return jsonify({
            "msg": "User updated successfully",
            "user": user.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Error updating user: {str(e)}"}), 500


@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_user(user_id):
    try:
        current_user_id = get_jwt_identity()

        if user_id == int(current_user_id):
            return jsonify({"msg": "Cannot delete your own account"}), 400

        user = User.query.get(user_id)

        if not user:
            return jsonify({"msg": "User not found"}), 404

        # Prevent deletion of last admin
        if user.role == ROLES['ADMIN']:
            admin_count = User.query.filter_by(role=ROLES['ADMIN']).count()
            if admin_count <= 1:
                return jsonify({"msg": "Cannot delete the last admin user"}), 400

        username = user.username
        db.session.delete(user)
        db.session.commit()

        return jsonify({
            "msg": f"User '{username}' deleted successfully"
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Error deleting user: {str(e)}"}), 500


# CSV UPLOAD

@admin_bp.route('/upload_csv', methods=['POST'])
@jwt_required()
@admin_required
def upload_csv():
    try:
        if 'file' not in request.files:
            return jsonify({"msg": "No file provided"}), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({"msg": "No file selected"}), 400

        if not file.filename.endswith('.csv'):
            return jsonify({"msg": "File must be a CSV"}), 400

        try:
            os.makedirs(os.path.dirname(PATHS['raw_csv']), exist_ok=True)
            file.save(PATHS['raw_csv'])
            print(f"File uploaded successfully to: {PATHS['raw_csv']}")
        except Exception as e:
            return jsonify({"msg": f"Error saving raw file: {str(e)}"}), 500

        print("Starting data pipeline...")
        processing_success = run_processor()

        if not processing_success:
            return jsonify({
                "msg": "File uploaded, but data processing failed. Check server logs.",
                "status": "processing_failed"
            }), 500

        memory_success = reload_data()

        if not memory_success:
            return jsonify({
                "msg": "Processed successfully, but failed to load into memory",
                "status": "partial_success"
            }), 500

        summary = get_data_summary()

        return jsonify({
            "msg": "Pipeline complete: Data uploaded, processed, and live!",
            "status": "success",
            "data_summary": summary
        }), 200

    except Exception as e:
        return jsonify({"msg": f"Pipeline failed: {str(e)}"}), 500


# STATISTICS

@admin_bp.route('/stats', methods=['GET'])
@jwt_required()
@admin_required
def get_admin_stats():
    try:
        from models import PredictionBatch, PredictionItem

        stats = {
            "users": {
                "total": User.query.count(),
                "admins": User.query.filter_by(role=ROLES['ADMIN']).count(),
                "managers": User.query.filter_by(role=ROLES['MANAGER']).count(),
                "owners": User.query.filter_by(role=ROLES['OWNER']).count(),
                "active": User.query.filter_by(is_active=True).count()
            },
            "predictions": {
                "total_batches": PredictionBatch.query.count(),
                "total_items": PredictionItem.query.count(),
                "pending": PredictionItem.query.filter_by(status='pending').count(),
                "approved": PredictionItem.query.filter_by(status='approved').count(),
                "rejected": PredictionItem.query.filter_by(status='rejected').count()
            },
            "data": get_data_summary()
        }

        return jsonify(stats), 200

    except Exception as e:
        return jsonify({"msg": f"Error getting stats: {str(e)}"}), 500