from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_owner = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    properties = db.relationship('Property', backref='owner', cascade='all, delete-orphan')
    messages_sent = db.relationship('Message', 
                                    foreign_keys='Message.tenant_id', 
                                    backref='tenant', 
                                    lazy='dynamic',
                                    cascade='all, delete-orphan')
    
    messages_received = db.relationship('Message', 
                                        foreign_keys='Message.owner_id', 
                                        backref='owner_user', 
                                        lazy='dynamic',
                                        cascade='all, delete-orphan')
    
    # ✅ ADDED: Favorites relationship
    favorites = db.relationship('Favorite', backref='user', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User {self.email}>'

class Property(db.Model):
    __tablename__ = 'properties'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    location = db.Column(db.String(150), nullable=False)
    rent = db.Column(db.Float, nullable=False)
    property_type = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Relationships
    property_messages = db.relationship('Message', 
                                        foreign_keys='Message.property_id', 
                                        backref='property', 
                                        lazy='dynamic',
                                        cascade='all, delete-orphan')

    images = db.relationship('PropertyImage', backref='property', cascade='all, delete-orphan')
    
    # ✅ ADDED: Favorites relationship for property
    favorites = db.relationship('Favorite', backref='property_rel', cascade='all, delete-orphan')

    def get_images(self):
        """Returns a list of image filenames for this property."""
        return [img.filename for img in self.images]
    
    def get_first_image(self):
        """Returns the first image filename, or None if no images."""
        if self.images:
            return self.images[0].filename
        return None

    def __repr__(self):
        return f'<Property {self.title}>'

class PropertyImage(db.Model):
    __tablename__ = 'property_images'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id'), nullable=False)
    # ✅ ADDED BACK: created_at field (useful for sorting images)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<PropertyImage {self.filename}>'

class Message(db.Model):
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    message_text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    tenant_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id'), nullable=False)

    def __repr__(self):
        return f'<Message {self.id}>'

class Favorite(db.Model):
    __tablename__ = 'favorites'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # ✅ FIXED: Added unique constraint to prevent duplicate favorites
    __table_args__ = (db.UniqueConstraint('user_id', 'property_id', name='unique_user_property_favorite'),)
    
    # Relationship
    property = db.relationship('Property', backref='favorited_by')
    
    def __repr__(self):
        return f'<Favorite user:{self.user_id} property:{self.property_id}>'