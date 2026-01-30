from flask import Flask, jsonify
from flask_cors import CORS
from extensions import db, bcrypt, jwt
from services import load_data_into_memory
from config import DevelopmentConfig, ProductionConfig
import os

# Import Blueprints
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.manager import manager_bp
from routes.owner import owner_bp
from routes.dashboard import dashboard_bp


def create_app(config_name='development'):
    app = Flask(__name__)

    # Load configuration
    if config_name == 'production':
        app.config.from_object(ProductionConfig)
    else:
        app.config.from_object(DevelopmentConfig)

    # Initialize extensions
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })

    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)

    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(manager_bp, url_prefix='/api/manager')
    app.register_blueprint(owner_bp, url_prefix='/api/owner')
    app.register_blueprint(dashboard_bp, url_prefix='/api')

    # Root route (health check)
    @app.route('/', methods=['GET'])
    def home():
        return jsonify({
            "status": "online",
            "version": "2.0.0",
            "mode": "production" if config_name == 'production' else "development",
            "api": {
                "auth": "/api/auth",
                "admin": "/api/admin",
                "manager": "/api/manager",
                "owner": "/api/owner",
                "dashboard": "/api"
            }
        }), 200

    # API info route
    @app.route('/api', methods=['GET'])
    def api_info():
        return jsonify({
            "name": "Fashion Trends Analysis API",
            "version": "2.0.0",
            "endpoints": {
                "authentication": {
                    "register": "POST /api/auth/register",
                    "login": "POST /api/auth/login",
                    "validate": "GET /api/auth/validate"
                },
                "admin": {
                    "users": "GET /api/admin/users",
                    "create_user": "POST /api/admin/users",
                    "update_user": "PUT /api/admin/users/<id>",
                    "delete_user": "DELETE /api/admin/users/<id>",
                    "upload_csv": "POST /api/admin/upload_csv",
                    "stats": "GET /api/admin/stats"
                },
                "manager": {
                    "generate_prediction": "POST /api/manager/generate_prediction",
                    "preview_prediction": "POST /api/manager/preview_prediction",
                    "predictions": "GET /api/manager/predictions",
                    "stats": "GET /api/manager/stats"
                },
                "owner": {
                    "pending_items": "GET /api/owner/pending_items",
                    "pending_batches": "GET /api/owner/pending_batches",
                    "update_status": "POST /api/owner/update_status",
                    "batch_update": "POST /api/owner/batch_update_status",
                    "approve_batch": "POST /api/owner/approve_batch/<batch_id>",
                    "review_history": "GET /api/owner/review_history",
                    "stats": "GET /api/owner/stats"
                },
                "dashboard": {
                    "taxonomy": "GET /api/taxonomy",
                    "hot_trends": "GET /api/hot_trends",
                    "analyze": "POST /api/analyze",
                    "category_breakdown": "GET /api/category_breakdown",
                    "search": "GET /api/search",
                    "available_filters": "GET /api/available_filters"
                }
            }
        }), 200

    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            "error": "Not Found",
            "msg": "The requested resource was not found"
        }), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            "error": "Internal Server Error",
            "msg": "An internal error occurred. Please try again later."
        }), 500

    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({
            "error": "Forbidden",
            "msg": "You don't have permission to access this resource"
        }), 403

    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({
            "error": "Unauthorized",
            "msg": "Authentication required or invalid credentials"
        }), 401

    # JWT error handlers
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({
            "error": "Invalid Token",
            "msg": "The token is invalid or malformed"
        }), 401

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_data):
        return jsonify({
            "error": "Token Expired",
            "msg": "The token has expired. Please login again."
        }), 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({
            "error": "Missing Token",
            "msg": "Authorization header is missing"
        }), 401

    # Initialize database and load data
    with app.app_context():
        # Create all tables
        db.create_all()
        print("Database tables created")
        # Load CSV data into memory
        data_loaded = load_data_into_memory()
        if data_loaded:
            print("CSV data loaded into memory")
        else:
            print("Warning: CSV data not loaded. Run data_processor.py first.")
        # Create default admin user if none exists
        from models import User
        if not User.query.filter_by(role='admin').first():
            # DELETE THIS LINE BELOW:
            # from extensions import bcrypt   <-- CAUSING THE ERROR
            # The code will now use the global 'bcrypt' imported at the very top
            default_admin = User(
                username='admin',
                password_hash=bcrypt.generate_password_hash('admin123').decode('utf-8'),
                role='admin'
            )
            db.session.add(default_admin)
            db.session.commit()

    return app


if __name__ == '__main__':
    # Determine environment
    env = os.environ.get('FLASK_ENV', 'development')

    # Create app
    app = create_app(config_name=env)

    # Run server
    port = int(os.environ.get('PORT', 5001))

    app.run(
        host='0.0.0.0',
        port=port,
        debug=(env == 'development')
    )