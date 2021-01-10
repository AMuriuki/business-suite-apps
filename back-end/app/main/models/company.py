from app import db


class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    settings = db.relationship('ConfigSettings', backref='settings', lazy='dynamic')
    company_name = db.Column(db.String(128))
    users = db.relationship('User', backref='accepted_users', lazy='dynamic')
    # logo = 
    street = db.Column(db.String(128))
    city = db.Column(db.String(128))
    
