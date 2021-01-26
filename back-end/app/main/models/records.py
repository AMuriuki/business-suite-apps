from app import db


class Record(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(128), index=True)
    fetchmailserver = db.relationship(
        'FetchmailServer', backref='fetchmail_record', lazy='dynamic')
    messages = db.relationship('Message', backref='thread', lazy='dynamic')
