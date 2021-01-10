from app import db


class Record(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(128), index=True)
    addresses = db.relationship(
        'MailAddress', backref='record', lazy='dynamic')
    fetchmailserver = db.relationship(
        'FetchmailServer', backref='fetchmail_record', lazy='dynamic')
    messages = db.relationship('MailMessage', backref='thread', lazy='dynamic')
