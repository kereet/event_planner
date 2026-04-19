from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import enum

db = SQLAlchemy()

class JoinStatus(enum.Enum):
    PENDING = 'pending'
    ACCEPTED = 'accepted'
    DECLINED = 'declined'

class EventStatus(enum.Enum):
    DRAFT = 'draft'
    PUBLISHED = 'published'
    FINISHED = 'finished'

class EventType(enum.Enum):
    CAFE = 'cafe'
    CINEMA = 'cinema'
    SHOPPING = 'shopping'
    OTHER = 'other'

class User(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    surname = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    created_events = db.relationship('Event', back_populates='creator', foreign_keys='Event.creator_id')
    votes = db.relationship('Vote', back_populates='user')
    memberships = db.relationship('EventMember', back_populates='user')

class Event(db.Model):
    __tablename__ = 'events'
    event_id = db.Column(db.Integer, primary_key=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    status = db.Column(db.Enum(EventStatus), default=EventStatus.DRAFT)
    event_type = db.Column(db.Enum(EventType), nullable=False)
    final_slot_id = db.Column(db.Integer, db.ForeignKey('event_slots.slot_id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    creator = db.relationship('User', back_populates='created_events', foreign_keys=[creator_id])
    slots = db.relationship('EventSlot', back_populates='event', foreign_keys='EventSlot.event_id')
    votes = db.relationship('Vote', back_populates='event')
    members = db.relationship('EventMember', back_populates='event')
    checklist_items = db.relationship('ChecklistItem', back_populates='event')
    final_slot = db.relationship('EventSlot', foreign_keys=[final_slot_id], uselist=False)

class EventSlot(db.Model):
    __tablename__ = 'event_slots'
    slot_id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.event_id'), nullable=False)
    time = db.Column(db.DateTime, nullable=False)
    place_name = db.Column(db.String(200), nullable=False)
    place_address = db.Column(db.String(300), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    
    event = db.relationship('Event', back_populates='slots', foreign_keys=[event_id])
    votes = db.relationship('Vote', back_populates='slot')
    creator = db.relationship('User', foreign_keys=[created_by])

class Vote(db.Model):
    __tablename__ = 'votes'
    vote_id = db.Column(db.Integer, primary_key=True)
    slot_id = db.Column(db.Integer, db.ForeignKey('event_slots.slot_id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('events.event_id'), nullable=False)
    preference = db.Column(db.Integer)
    
    slot = db.relationship('EventSlot', back_populates='votes')
    user = db.relationship('User', back_populates='votes')
    event = db.relationship('Event', back_populates='votes')
    __table_args__ = (db.UniqueConstraint('slot_id', 'user_id', name='unique_vote'),)

class ChecklistItem(db.Model):
    __tablename__ = 'checklist_items'
    item_id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.event_id'), nullable=False)
    text = db.Column(db.String(500), nullable=False)
    is_completed = db.Column(db.Boolean, default=False)
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=True)
    
    event = db.relationship('Event', back_populates='checklist_items')

class EventMember(db.Model):
    __tablename__ = 'event_members'
    event_member_id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.event_id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    join_status = db.Column(db.Enum(JoinStatus), default=JoinStatus.PENDING)
    invite_token = db.Column(db.String(100), unique=True, nullable=False)
    
    event = db.relationship('Event', back_populates='members')
    user = db.relationship('User', back_populates='memberships')