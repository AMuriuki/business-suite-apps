# -*- coding:utf-8 -*-
# Part of Teleios. See LICENSE file for full copyright and licensing details.

import logging
import poplib
import enum
import json
from imaplib import IMAP4, IMAP4_SSL
from poplib import POP3, POP3_SSL
from datetime import datetime, timedelta

from app import db
from app.models import SearchableMixin
from app.mail.models.mail_thread import MailThreadMixin
from app.mail.models.message import MailMessage


_logger = logging.getLogger(__name__)
MAX_POP_MESSAGES = 50
MAIL_TIMEOUT = 60

# Workaround for python 2.7.8 bug https://bugs.python.org/issue23906
poplib._MAXLINE = 65536


class StateEnum(enum.Enum):
    draft = 'Not Confirmed'
    done = 'Confirmed'


class ServertypeEnum(enum.Enum):
    pop = 'POP Server'
    imap = 'IMAP Server'
    local = 'Local Server'


class FetchmailServer(MailThreadMixin, db.Model):
    """Incoming POP/IMAP mail server account"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False, name="Name")
    active = db.Column(db.Boolean, default=True, name="Active")

    state = db.Column(
        db.Enum(StateEnum),
        default=StateEnum.draft,
        index=True,
        nullable=False,
        name="Status"
    )

    # Hostname or IP of the mail server"
    server = db.Column(db.String(128), name="Server Name")
    port = db.Column(db.Integer)
    server_type = db.Column(
        db.Enum(ServertypeEnum),
        default=ServertypeEnum.pop,
        index=True,
        nullable=False,
        name="Server Type"
    )

    # Connections are encrypted with SSL/TLS through a dedicated port (default: IMAP=993, POP3S=995")
    is_ssl = db.Column(db.Boolean, name="SSL/TLS", default=True)

    # Whether attachments should be downloaded.
    # If not enabled, incoming emails will be stripped of any attachments before being processed"
    attach = db.Column(db.Boolean, name="Keep Attachments", default=True)

    # Whether a full original copy of each email should be kept for reference and attached to each processed message.
    # This will usually double the size of your message database."
    original = db.Column(db.Boolean, name="Keep original")

    date = db.Column(db.DateTime, name="Last Fetch Date")
    user = db.Column(db.String(128), name="Username")
    password = db.Column(db.String(128))

    # Process each incoming mail as part of a conversation corresponding to this document type.
    # This will create new documents for new conversations,
    # or attach follow-up emails to the existing conversations (documents)
    record_id = db.Column(db.Integer, db.ForeignKey('record.id'))

    # Defines the order of processing, lower values mean higher priority", default=5)
    priority = db.Column(db.String(128), name="Server Priority")
    messages = db.relationship(
        MailMessage, foreign_keys=MailMessage.fetchmailserver_id, backref="Messages")
    configuration = db.Column(db.Text(), name="Configuration")
    # script

    def connect(self):
        if self.server_type.value == 'IMAP Server':
            if self.is_ssl:
                connection = IMAP4_SSL(self.server, int(self.port))
            else:
                connection = IMAP4(self.server, int(self.port))
            connection.login(self.user, self.password)
        elif self.server_type.value == 'POP Server':
            if self.is_ssl:
                connection = POP3_SSL(self.server, int(self.port))
            else:
                connection = POP3(self.server, int(self.port))
            # TODO: use this to remove only unread messages
            # connection.user("recent:"+server.user)
            connection.user(self.user)
            connection.pass_(self.password)
        # Add timout on socket
        connection.sock.settimeout(MAIL_TIMEOUT)
        print(connection)
        return connection

    def fetch_mail(self):
        """WARNING: meant for cron usage only - will commit() after each email!"""
        count, failed = 0, 0
        imap_server = None
        pop_server = None
        if self.server_type.value == 'IMAP Server':
            print("Server Type is IMAP Server")
            _logger.info('start checking for new emails on %s server %s',
                         self.server_type.value, self.name)
            try:
                imap_server = self.connect()
                imap_server.select()
                result, data = imap_server.search(None, '(UNSEEN)')
                msgs = []
                for num in data[0].split():
                    res_id = None
                    result, data = imap_server.fetch(num, '(RFC822)')
                    imap_server.store(num, '-FLAGS', '\\Seen')
                    try:
                        # res_id = MailThreadMixin.message_process(
                        #     self.record_id, data[0][1], save_original=self.original, strip_attachments=(not self.attach))
                        msg_dict = MailThreadMixin.message_process(
                            self.record_id, data[0][1], save_original=self.original, strip_attachments=(not self.attach))
                        msgs.append(msg_dict)
                    except Exception as e:
                        print(e)
                if msgs:
                    with open("inbox.json", "w", encoding='utf-8') as outfile:
                            json.dump(msgs, outfile,
                                      ensure_ascii=False, indent=4)
                    print("success")
            except Exception as e:
                print(e)
