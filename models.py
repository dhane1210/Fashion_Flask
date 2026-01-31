from extensions import db
from datetime import datetime


class User(db.Model):

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin, manager, owner
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    # Relationship to predictions created by this user
    predictions = db.relationship('PredictionBatch', backref='creator', lazy=True)

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_active': self.is_active
        }


class PredictionBatch(db.Model):
    __tablename__ = 'prediction_batches'

    uni_id = db.Column(db.String(50), primary_key=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Filter Parameters
    region = db.Column(db.String(50))
    season = db.Column(db.String(50))
    gender = db.Column(db.String(20))
    age_group = db.Column(db.String(20))

    # Relationship to prediction items
    items = db.relationship('PredictionItem', backref='batch', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<PredictionBatch {self.uni_id}>'

    def to_dict(self, include_items=False):
        result = {
            'uni_id': self.uni_id,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'region': self.region,
            'season': self.season,
            'gender': self.gender,
            'age_group': self.age_group,
            'items_count': len(self.items)
        }

        if include_items:
            result['items'] = [item.to_dict() for item in self.items]

        return result


class PredictionItem(db.Model):
    __tablename__ = 'prediction_items'

    id = db.Column(db.Integer, primary_key=True)
    uni_id = db.Column(db.String(50), db.ForeignKey('prediction_batches.uni_id'), nullable=False, index=True)

    # Product Attributes
    product = db.Column(db.String(100), nullable=False)
    color = db.Column(db.String(50))
    fabric = db.Column(db.String(50))
    style = db.Column(db.String(50))

    # Approval Status: 'pending', 'approved', 'rejected'
    status = db.Column(db.String(20), default='pending', index=True)
    reviewed_at = db.Column(db.DateTime)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    def __repr__(self):
        return f'<PredictionItem {self.id}: {self.product} - {self.status}>'

    def to_dict(self):
        return {
            'id': self.id,
            'uni_id': self.uni_id,
            'product': self.product,
            'color': self.color,
            'fabric': self.fabric,
            'style': self.style,
            'status': self.status,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'reviewed_by': self.reviewed_by
        }