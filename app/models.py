from . import db
from flask_login import UserMixin
from . import login_manager
from datetime import date

class Users(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(10), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))

class Products(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    stock = db.Column(db.Integer, default=0)
    price = db.Column(db.Integer, nullable=False)
    image = db.Column(db.String, nullable=True)


class Sale(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    member_id = db.Column(db.Integer(), db.ForeignKey('members.id'), nullable=True)
    total_price = db.Column(db.Float(), nullable=False)
    created_by = db.Column(db.String(50), nullable=False)
    member_status =  db.Column(db.String(25), nullable=True, default="Non-member")
    created_at = db.Column(db.Date(), default=date.today)

    member = db.relationship("Members", backref="sale", lazy=True)


class Members(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=True)
    phone_number = db.Column(db.String(20), unique=True, nullable=False)
    points = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=date.today)

class saleDetails(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    sale_id = db.Column(db.Integer(), db.ForeignKey('sale.id'))
    member_id = db.Column(db.Integer(), db.ForeignKey('members.id'), nullable=True)
    member_since = db.Column(db.Date, nullable=True)
    member_point = db.Column(db.Float(), nullable=True)
    invoice = db.Column(db.String(25), nullable=False)
    product_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer(), nullable=False)
    product_price = db.Column(db.Float(), nullable=False)
    total_price = db.Column(db.Float(), nullable=False)
    total_pay = db.Column(db.Float(), nullable=False)
    used_point = db.Column(db.Float(), default=0.0, nullable=True)
    refund = db.Column(db.Float(), default=0.0, nullable=True)
    
    member = db.relationship("Members", backref="sale_detail", lazy=True)
    sale = db.relationship("Sale", backref="sale_detail", lazy=True)



