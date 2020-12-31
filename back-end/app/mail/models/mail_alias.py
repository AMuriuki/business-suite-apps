# -*- coding: utf-8 -*-

import logging
import re

from app import db

_logger = logging.getLogger(__name__)

# see rfc5322 section 3.2.3
atext = r"[a-zA-Z0-9!#$%&'*+\-/=?^_`{|}~]"
dot_atom_text = re.compile(r"^%s+(\./%s+)*$" % (atext, atext))


class Alias(db.Model):
    """
    A Mail Alias is a mapping of an email address with a given Teleios document
    model. It is used by Teleios' mail gateway when processing incoming emails
    sent to the system. If the recipient address (To) of the message matches 
    a Mail Alias, the message will be either processed following the rules of 
    the alias. If the message is a reply it will be attached to the existing 
    discussion on the corresponding record, otherwise a new record of the 
    corresponding model will be created.

    This is meant to be used in combination with a catch-all email configuration
    on the company's mail server, so that as soon as a new mail.alias is created, 
    it becomes immediately usable and Teleios will accept email for it
    """
    id = db.Column(db.String(36), primary_key=True)

    # The name of the email alias e.g 'jobs'
    # If you want to catch emails for <jobs@example.com>
    alias_name = db.Column(db.String(128), name="Alias Name")

    # Teleios document to which this alias corresponds e.g Contacts, Sales Team, Discussion Channel
    alias_record_id = db.Column(db.Integer, db.ForeignKey('record.id'))

    # The owner of records created upon receiving emails on this alias
    alias_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    # Python dict that will be evaluated to provide default
    # values when creating new records for this alias
    alias_default = db.Column(db.Text(), name="Default Values")

    alias_domain = db.Column(db.String(128), name="Alias Domain")
