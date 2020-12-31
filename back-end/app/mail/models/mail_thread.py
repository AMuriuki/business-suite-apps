
import email
try:
    from xmlrpc import client as xmlrpclib
except ImportError:
    import xmlrpclib
from email.message import Message
from flask_babel import _
import time
import datetime
import logging
import pytz
import dateutil
import lxml
import json

from app.mail.tools import tools_mail
from collections import namedtuple
from lxml import etree

from app import db
from app.mail.models.message import MailMessage


_logger = logging.getLogger(__name__)


class MailThreadMixin(object):
    """MailThreadMixin is meant to be inherited by any model
    that needs to act as a discussion topic on which messages
    can be attached."""

    _Attachment = namedtuple('Attachment', ('fname', 'content', 'info'))

    @classmethod
    def message_route(self, message, message_dict, model=None, thread_id=None, custom_values=None):
        """Attempt to figure out the correct target model, thread_id,
        custom_values and user_id to use for an incoming message.
        Multiple values may be returned, if a message had multiple
        recipients matching existing mail aliases, for example:

        The following heuristics are used, in this order:
         * if the message replies to an existing thread by having a Message-Id
           that matches an existing message.id, we take the original message
           model/thread_id pair and ignore the custom_value as no creation will
           take place;
         * look for a mail_alias entry matching the message recipients and use
           the corresponding model, thread_id, custom_values and user_id. This
           could lead to a thread update or creation depending on the alias;
         * fallback on provided ```model```, ```thread_id``` and ```custom_values```;
         * raise an exception as no route has been found

        :param string message: an email.message instance
        :param dict message_dict: dictionary holding parsed message variables
        :param string model: the fallback model to use if the message does not match
            any of the currently configured mail aliases (may be None if a matching
            alias is supposed to be present)
        :type dict custom_values: optional dictionary of default field values
            to pass to ```message_new``` if a new record needs to be created.
            Ignored if the thread record already exists, and also if a matching
            mail_alias was found (aliases define their own defaults)
        :param int thread_id: optional ID of the record/thread from ```model``` to 
            which this mail should be attached and does not match any mail alias.
        :return: list of routes [(model, thread_id, custom_values, user_id, alias)]

        :raises: ValueError, TypeError
        """
        if not isinstance(message, Message):
            raise TypeError(
                'message must be an email.message.Message at this point')
        # catchall_alias =
        # TODO: To be continued...

    @classmethod
    def message_process(self, model, message, custom_values=None, save_original=False, strip_attachments=False, thread_id=None):
        """Process an incoming RFC2822 email message, relying on ```mail.message.parse()``` for the parsing operation, and ```message_route()``` to figure out the target model.

        Once the target model is known, its ```message_new``` method is called with the new message(if the thread record did not exist) or its ```message_update``` method(if it did)."""

        # extract message bytes - we are forced to pass the message as binary because
        # we don't know its encoding until we parse its headers
        if isinstance(message, xmlrpclib.Binary):
            message = bytes(message.data)
        if isinstance(message, str):
            message = message.encode('utf-8')
        message = email.message_from_bytes(message)

        # parse the message, verify we are not in a loop by checking message_id is not duplicated
        msg_dict = self.message_parse(message, save_original=save_original)

        if strip_attachments:
            msg_dict.pop('attachments', None)

        existing_msg_id = db.session.query(MailMessage).filter_by(
            message_id=msg_dict['message_id']).first()

        if existing_msg_id:
            _logger.info('Ignored mail from %s to %s with Message-Id %s: found duplicated Message-Id during processing',
                         msg_dict.get('email_from'), msg_dict.get('to'), msg_dict.get('message_id'))
            return False
        return msg_dict

        # TODO: Uncomment only when need be.
        # routes = self.message_route(
        #     message, msg_dict, model, thread_id, custom_values)

    @classmethod
    def _message_parse_extract_payload_postprocess(self, message, payload_dict):
        """ Perform some cleaning / postprocess in the body and attachments
        extracted from the email. Note that this processing is specific to the
        mail module, and should not contain security or generic html cleaning.
        Indeed those aspects should be covered by the html_sanitize method
        located in tools. """
        body, attachments = payload_dict['body'], payload_dict['attachments']
        if not body:
            return payload_dict
        try:
            root = lxml.html.fromstring(body)
        except ValueError:
            # In case the email client sent XHTML, fromstring will fail because 'Unicode strings
            # with encoding declaration are not supported'.
            root = lxml.html.fromstring(body.encode('utf-8'))

        postprocessed = False
        to_remove = []
        for node in root.iter():
            if 'o_mail_notification' in (node.get('class') or '') or 'o_mail_notification' in (node.get('summary') or ''):
                postprocessed = True
                if node.getparent() is not None:
                    to_remove.append(node)
            if node.tag == 'img' and node.get('src', '').startswith('cid:'):
                cid = node.get('src').split(':', 1)[1]
                related_attachment = [
                    attach for attach in attachments if attach[2] and attach[2].get('cid') == cid]
                if related_attachment:
                    node.set('data-filename', related_attachment[0][0])
                    postprocessed = True

        for node in to_remove:
            node.getparent().remove(node)
        if postprocessed:
            body = etree.tostring(root, pretty_print=False, encoding='unicode')
        return {'body': body, 'attachments': attachments}

    @classmethod
    def _message_parse_extract_payload(self, message, save_original=False):
        """Extract body as HTML and attachments from the mail message"""
        attachments = []
        body = u''
        if save_original:
            attachments.append(self._Attachment(
                'original_email.eml', message.as_string(), {}))

        # Be careful, content-type may contain tricky content like in the
        # following example so test the MIME type with startswith()
        #
        # Content-Type: multipart/related;
        #   boundary="_004_3f1e4da175f349248b8d43cdeb9866f1AMSPR06MB343eurprd06pro_"
        #   type="text/html"
        if message.get_content_maintype() == 'text':
            encoding = message.get_content_charset()
            body = message.get_payload(decode=True)
            body = tools_mail.ustr(body, encoding, errors='replace')
            if message.get_content_type() == 'text/plain':
                # text/plain -> <pre/>
                body = tools_mail.append_content_to_html(
                    u'', body, preserve=True)
        else:
            alternative = False
            mixed = False
            html = u''
            for part in message.walk():
                if part.get_content_type() == 'multipart/alternative':
                    alternative = True
                if part.get_content_type() == 'multipart/mixed':
                    mixed = True
                if part.get_content_maintype() == 'multipart':
                    continue  # skip container
                # part.get_filename returns decoded value if able to decode, coded otherwise.
                # original get_filename is not able to decode iso-8859-1 (for instance).
                # therefore, iso encoded attachements are not able to be decoded properly with get_filename
                # code here partially copy the original get_filename method, but handle more encoding
                filename = part.get_param(
                    'filename', None, 'content-disposition')
                if not filename:
                    filename = part.get_param('name', None)
                if filename:
                    if isinstance(filename, tuple):
                        # RFC2231
                        filename = email.utils.collapse_rfc2231_value(
                            filename).strip()
                    else:
                        filename = tools_mail.decode_smtp_header(filename)
                encoding = part.get_content_charset()  # None if attachment

                # 0) Inline Attachments -> attachments, with a third part in the tuple to match cid / attachment
                if filename and part.get('content-id'):
                    inner_cid = str(part.get('content-id')).strip('><')
                    attachments.append(self._Attachment(
                        filename, part.get_payload(decode=True), {'cid': inner_cid}))
                    continue
                # 1) Explicit Attachments -> attachments
                if filename or part.get('content-disposition', '').strip().startswith('attachment'):
                    attachments.append(self._Attachment(
                        filename or 'attachment', part.get_payload(decode=True), {}))
                    continue
                # 2) text/plain -> <pre/>
                if part.get_content_type() == 'text/plain' and (not alternative or not body):
                    body = tools_mail.append_content_to_html(body, tools_mail.ustr(part.get_payload(decode=True),
                                                                                   encoding, errors='replace'), preserve=True)
                # 3) text/html -> raw
                elif part.get_content_type() == 'text/html':
                    # mutlipart/alternative have one text and a html part, keep only the second
                    # mixed allows several html parts, append html content
                    append_content = not alternative or (html and mixed)
                    html = tools_mail.ustr(part.get_payload(
                        decode=True), encoding, errors='replace')
                    if not append_content:
                        body = html
                    else:
                        body = tools_mail.append_content_to_html(
                            body, html, plaintext=False)
                    # we only strip_classes here everything else will be done in by html field of mail.message
                    body = tools_mail.html_sanitize(
                        body, sanitize_tags=False, strip_classes=True)
                # 4) Anything else -> attachment
                else:
                    attachments.append(self._Attachment(
                        filename or 'attachment', part.get_payload(decode=True), {}))
                
        return self._message_parse_extract_payload_postprocess(message, {'body': body, 'attachments': attachments})

    @classmethod
    def _message_parse_extract_bounce(self, email_message, message_dict):
        """ Parse email and extract bounce information to be used in future
            processing.

            : param email_message: an email.message instance;
            : param message_dict: dictionary holding already-parsed values and in
                which bounce-related values will be added;
            """

        if not isinstance(email_message, Message):
            raise TypeError(
                'message must be an email.message.Message at this point')

        email_part = next((part for part in email_message.walk()
                           if part.get_content_type() == 'message/rfc822'), None)
        dsn_part = next((part for part in email_message.walk(
        ) if part.get_content_type() == 'message/delivery-status'), None)

        bounced_email = False
        # bounced_partner = self.env['res.partner'].sudo()
        if dsn_part and len(dsn_part.get_payload()) > 1:
            dsn = dsn_part.get_payload()[1]
            final_recipient_data = tools_mail.decode_message_header(
                dsn, 'Final-Recipient')
            bounced_email = tools_mail.email_normalize(
                final_recipient_data.split(';', 1)[1].strip())
            if bounced_email:
                pass
                # bounced_partner = self.env['res.partner'].sudo().search(
                #     [('email_normalized', '=', bounced_email)])

        bounced_msg_id = False
        # bounced_message = self.env['mail.message'].sudo()
        bounced_message = False
        if email_part:
            email = email_part.get_payload()[0]
            bounced_msg_id = tools_mail.mail_header_msgid_re.findall(
                tools_mail.decode_message_header(email, 'Message-Id'))
            if bounced_msg_id:
                pass
                # bounced_message = self.env['mail.message'].sudo().search(
                #     [('message_id', 'in', bounced_msg_id)])

        return {
            'bounced_email': bounced_email,
            'bounced_partner': None,
            'bounced_msg_id': bounced_msg_id,
            'bounced_message': bounced_message,
        }

    @classmethod
    def message_parse(self, message, save_original=False):
        """Parse an email message representing an RFC-2822 email and returns a generic dict holding the message details.

        : param message: email to parse
        : return: A dict with the following structure, where each field may not be present if missing in original message: :
            {
                'message_id': msg_id,
                'subject': subject,
                'email_from': from,
                'to': to + delivered-to,
                'cc': cc,
                'recipients': delivered-to + to + cc + resent-to + resent-cc,
                'partner_ids': partners found based on recipients emails,
                'body': unified_body,
                'references': references,
                'in_reply_to': in -reply-to,
                'parent_id': parent message based on in_reply_to or references,
                'internal': answer to an internal message(note),
                'date': date,
                'attachments': [('file1', 'bytes'),
                                ('file2', 'bytes')]
            }
        """

        if not isinstance(message, Message):
            raise ValueError(_('Message should be a valid Message instance'))
        msg_dict = {'message': 'email'}

        message_id = message.get('Message-Id')

        if not message_id:
            # Very unusual situation, but we should be fault-tolerant here
            message_id = "<%s@localhost>" % time.time()
            _logger.debug(
                'Parsing Message without message-id, generating a random one: %s', message_id)
        msg_dict['message_id'] = message_id.strip()

        if message.get('Subject'):
            msg_dict['subject'] = tools_mail.decode_message_header(
                message, 'Subject')

        email_from = tools_mail.decode_message_header(
            message, 'From')
        email_cc = tools_mail.decode_message_header(message, 'cc')
        email_from_list = tools_mail.email_split_and_format(email_from)
        email_cc_list = tools_mail.email_split_and_format(email_cc)
        msg_dict['email_from'] = email_from_list[0] if email_from_list else email_from
        # compatibilty for message_new
        msg_dict['from'] = msg_dict['email_from']
        msg_dict['cc'] = ','.join(email_cc_list) if email_cc_list else email_cc
        msg_dict['recipients'] = ','.join(set(formatted_email for address in [
            tools_mail.decode_message_header(
                message, 'Delivered-To'),
            tools_mail.decode_message_header(message, 'To'),
            tools_mail.decode_message_header(message, 'Cc'),
            tools_mail.decode_message_header(
                message, 'Resent-To'),
            tools_mail.decode_message_header(
                message, 'Resent-Cc'),
        ] if address for formatted_email in tools_mail.email_split_and_format(address)))
        msg_dict['to'] = ','.join(set(formatted_email for address in [
            tools_mail.decode_message_header(
                message, 'Delivered-To'),
            tools_mail.decode_message_header(message, 'To')
        ] if address for formatted_email in tools_mail.email_split_and_format(address)))

        # partner_ids = [x.id for x in self._mail_find_partner_from_emails(
        #     tools_mail.email_split(msg_dict['recipients']), records=self) if x]

        # compute references to find if email_message is a reply to an existing thread
        msg_dict['references'] = tools_mail.decode_message_header(
            message, 'References')
        msg_dict['in_reply_to'] = tools_mail.decode_message_header(
            message, 'In-Reply-To').strip()

        if message.get('Date'):
            try:
                date_hdr = tools_mail.decode_message_header(message, 'Date')
                parsed_date = dateutil.parser.parse(date_hdr, fuzzy=True)
                if parsed_date.utcoffset() is None:
                    # naive datetime, so we arbitrarily decide to make it
                    # UTC, there's no better choice. Should not happen,
                    # as RFC2822 requires timezone offset in Date headers
                    stored_date = parsed_date.replace(tzinfo=pytz.utc)
                else:
                    stored_date = parsed_date.astimezone(tz=pytz.utc)
            except Exception:
                _logger.info(
                    'Failed to parse Date header %r in incoming mail with message-id %r, assuming current date/time.', message.get('Date'), message_id)
                stored_date = str(datetime.datetime.now())
            msg_dict['date'] = message.get('Date')

        if msg_dict['in_reply_to']:
            reply_message = db.session.query(MailMessage).filter_by(
                message_id=msg_dict['in_reply_to']).all()
            if reply_message:
                msg_dict['parent_id'] = reply_message.id
                # msg_dict['internal'] = parent_ids.subtype_id and parent_ids.subtype_id.internal or False

        # if msg_dict['references'] and 'parent_id' not in msg_dict:
        #     references_msg_id_list = tools_mail.mail_header_msgid_re.findall(
        #         msg_dict['references'])
        #     parent_ids = self.search(
        #         [('message_id', 'in', [x.strip() for x in references_msg_id_list])], limit=1)
        #     if parent_ids:
        #         msg_dict['parent_id'] = parent_ids.id
        #         msg_dict['internal'] = parent_ids.subtype_id and parent_ids.subtype_id.internal or False

        msg_dict.update(self._message_parse_extract_payload(
            message, save_original=save_original))
        msg_dict.update(self._message_parse_extract_bounce(message, msg_dict))
        return msg_dict
