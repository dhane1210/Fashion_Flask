from flask import Blueprint, request, jsonify
from extensions import db, bcrypt
from models import User
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token, get_jwt
from config import ROLES

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()

        # Validation
        if not data:
            return jsonify({"msg": "No data provided"}), 400

        required_fields = ['username', 'password', 'role']
        for field in required_fields:
            if field not in data:
                return jsonify({"msg": f"Missing required field: {field}"}), 400

        # Validate role
        valid_roles = [ROLES['ADMIN'], ROLES['MANAGER'], ROLES['OWNER']]
        if data['role'] not in valid_roles:
            return jsonify({"msg": f"Invalid role. Must be one of: {', '.join(valid_roles)}"}), 400

        # Check if username already exists
        if User.query.filter_by(username=data['username']).first():
            return jsonify({"msg": "Username already exists"}), 409

        # Validate password strength
        if len(data['password']) < 6:
            return jsonify({"msg": "Password must be at least 6 characters"}), 400

        # Hash password
        hashed_pw = bcrypt.generate_password_hash(data['password']).decode('utf-8')

        # Create user
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
        return jsonify({"msg": f"Registration failed: {str(e)}"}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()

        # Validation
        if not data:
            return jsonify({"msg": "No data provided"}), 400

        if 'username' not in data or 'password' not in data:
            return jsonify({"msg": "Username and password required"}), 400

        # Find user
        user = User.query.filter_by(username=data['username']).first()

        if not user:
            return jsonify({"msg": "Invalid username or password"}), 401

        # Check if user is active
        if not user.is_active:
            return jsonify({"msg": "Account is deactivated"}), 403

        # Verify password
        if not bcrypt.check_password_hash(user.password_hash, data['password']):
            return jsonify({"msg": "Invalid username or password"}), 401

        # Create JWT token with user info
        token = create_access_token(
            identity=str(user.id),
            additional_claims={
                "username": user.username,
                "role": user.role
            }
        )

        return jsonify({
            "access_token": token,
            "user": user.to_dict()
        }), 200

    except Exception as e:
        return jsonify({"msg": f"Login failed: {str(e)}"}), 500


@auth_bp.route('/validate', methods=['GET'])
@jwt_required()
def validate_token():
    try:
        current_user_id = get_jwt_identity()
        claims = get_jwt()

        user_data = {
            "id": current_user_id,
            "username": claims.get("username"),
            "role": claims.get("role")
        }

        return jsonify({
            "valid": True,
            "user": user_data
        }), 200

    except Exception as e:
        return jsonify({"valid": False, "msg": str(e)}), 500