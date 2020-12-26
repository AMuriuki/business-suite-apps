# -*- coding:utf-8 -*-
# Part of Teleios. See LICENSE file for full copyright and licensing details.

from app import db
from app.mail.models.message import Message


class Mail(db.Model):
    """Models holding RFC2822 email messages to send. This model also provides facilities to queue and send new email messages"""
    id = db.Column(db.Integer, primary_key=True)
