# -*- coding:utf-8 -*-
# Part of Teleios. See LICENSE file for full copyright and licensing details.

import logging
import poplib
import enum
from imaplib import IMAP4, IMAP4_SSL
from poplib import POP3, POP3_SSL
from datetime import datetime, timedelta

from app import db
from app.models import BasemodelMixin


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


class FetchmailServer(BasemodelMixin, db.Model):
    """Incoming POP/IMAP mail server account"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False, name="Name")
    active = db.Column(db.Boolean, default=True, name="Active")

    # Hostname or IP of the mail server"
    state = db.Column(
        db.Enum(StateEnum),
        default=StateEnum.draft,
        index=True,
        nullable=False,
        name="Status"
    )
    
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
    is_ssl = db.Column(db.String(128), name="SSL/TLS")

    # Whether attachments should be downloaded. 
    # If not enabled, incoming emails will be stripped of any attachments before being processed"
    attach = db.Column(db.Boolean, name="Keep Attachments", default=True)

    # Whether a full original copy of each email should be kept for reference and attached to each processed message. 
    # This will usually double the size of your message database."
    original = db.Column(db.String(128), name="Keep original")

    date = db.Column(db.DateTime, name="Last Fetch Date")
    user = db.Column(db.String(128), name="Username")
    password = db.Column(db.String(128))
    
    # Process each incoming mail as part of a conversation corresponding to this document type. 
    # This will create new documents for new conversations, 
    # or attach follow-up emails to the existing conversations (documents)
    # object_id = 

    # Defines the order of processing, lower values mean higher priority", default=5)
    priority = db.Column(db.String(128), name="Server Priority")
    message_ids = db.relationship(
        Message, foreign_keys=Message.id, backref="Messages")
    configuration = db.Column(db.Text(), name="Configuration")
    # script

    def connect(self):
        if self.server_type == 'imap':
            if self.is_ssl:
                connection = IMAP4_SSL(self.server, int(self.port))
            else:
                connection = IMAP4(self.server, int(self.port))
            connection.login(self.user, self.password)
        elif self.server_type == 'pop':
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
        return connection

    def fetch_mail(self):
        """WARNING: meant for cron usage only - will commit() after each email!"""
        additional_context = {
            'fetchmail_cron_running': True
        }
        MailThread = self.env['mail.thread']
        for server in self:
            _logger.info('start checking for new emails on %s server %s',
                         server.server_type, server.name)
            additional_context['default_fetchmail_server_id'] = server.id
            count, failed = 0, 0
            imap_server = None
            pop_server = None
            if server.server_type == 'imap':
                try:
                    imap_server = server.connect()
                    imap_server.select()
                    result, data = imap_server.search(None, '(UNSEEN)')
                    for num in data[0].split():
                        res_id = None
                        result, data = imap_server.fetch(num, '(RFC822)')
                        imap_server.store(num, '-FLAGS', '\\Seen')
                        try:
                            res_id = MailThread.with_context(**additional_context).message_process(
                                server.object_id.model, data[0][1], save_original=server.original, strip_attachments=(not server.attach))
                        except Exception:
                            _logger.info('Failed to process mail from %s server %s.',
                                         server.server_type, server.name, exc_info=True)
                            failed += 1
                        imap_server.store(num, '+FLAGS', '\\Seen')
                        db.session.add(self)
                        db.session.commit()
                        count += 1
                    _logger.info("Fetched %d email(s) on %s server %s; %d succeeded, %d failed.",
                                 count, server.server_type, server.name, exc_info=True)
                except Exception:
                    _logger.info("General failure when trying to fetch mail from %s server %s.",
                                 server.server_type, server.name, exc_info=True)
                finally:
                    if imap_server:
                        imap_server.close()
                        imap_server.logout()
            elif server.server_type == 'pop':
                try:
                    while True:
                        pop_server = server.connect()
                        (num_messages, total_size) = pop_server.stat()
                        pop_server.list()
                        for num in range(1, min(MAX_POP_MESSAGES, num_messages) + 1):
                            (header, messages, octets) = pop_server.retr(num)
                            message = (b'\n').join(messages)
                            res_id = None
                            try:
                                res_id = MailThread.with_context(**additional_context).message_process(
                                    server.object_id.model, message, save_original=server.original, strip_attachments=(not server.attach))
                                pop_server.dele(num)
                            except Exception:
                                _logger.info('Failed to process mail from %s server %s.',
                                             server.server_type, server.name, exc_info=True)
                                failed += 1
                            db.session.add(self)
                            db.session.commit()
                        if num_messages < MAX_POP_MESSAGES:
                            break
                        pop_server.quit()
                        _logger.info(
                            "Fetched %d email(s) on %s server %s; %d succeeded, %d failed.",
                            num_messages, server.server_type, server.name, (num_messages - failed), failed)
                except Exception:
                    _logger.info("General failure when trying to fetch mail from %s server %s.",
                                 server.server_type, server.name, exc_info=True)
                finally:
                    if pop_server:
                        pop_server.quit()
            # server.write({'date': fields.Datetime.now()})
        return True
