# -*- coding:utf-8 -*-
# Part of Teleios. See LICENSE file for full copyright and licensing details.

from app import db
from datetime import datetime, timedelta


class MailMessage(db.Model):
    """Messages model: system notification (replacing res.log notifications), comments (OpenChatter discussion) and incoming emails"""
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.String(128), index=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    in_reply_to = db.Column(db.String(128), index=True)
    # date = db.Column(db.String(128), index=True)
    fetchmailserver_id = db.Column(
        db.Integer, db.ForeignKey('fetchmail_server.id'))
    body = db.Column(db.String(140))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    def __repr__(self):
        return '<Message {}>'.format(self.body)
