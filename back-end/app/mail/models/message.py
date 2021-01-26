# -*- coding:utf-8 -*-
# Part of Teleios. See LICENSE file for full copyright and licensing details.
import enum
from app import db
from datetime import datetime, timedelta


class MessageTypeEnum(enum.Enum):
    email = 'Email'
    comment = 'Comment'
    notification = 'System Notification'
    user_notification = 'User Specific Notification'


class Message(db.Model):
    """
    Messages model: system notification, 
    comments (OpenChatter discussion), direct/inbox messages, and incoming emails
    """
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(128))
    date = db.Column(db.String(128))
    body = db.Column(db.Text())
    # attachment_id =
    parent_id = db.Column(db.Integer, db.ForeignKey('message.id'))
    message_id = db.Column(db.String(128), index=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    in_reply_to = db.Column(db.String(128), index=True)
    # date = db.Column(db.String(128), index=True)
    fetchmailserver_id = db.Column(
        db.Integer, db.ForeignKey('fetchmail_server.id'))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    children = db.relationship('Message', backref=('parent'), remote_side=id)
    record_id = db.Column(db.Integer, db.ForeignKey('record.id'))
    # record_name = db.Column(db.String(128))
    message_type = db.Column(
        db.Enum(MessageTypeEnum),
        default=MessageTypeEnum.email,
        index=True,
        nullable=False
    )
    email_from = db.Column(db.String(128))
    # author = db.Column(db.String(128))
    recipients = db.Column(db.Text())
    # channel_id = 
    # starred = 
    # reply_to = db.Column(db.String(128))
    # mail_server_id = outgoing mail server

    def __repr__(self):
        return '<Message {}>'.format(self.body)
