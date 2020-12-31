import sys
import base64
import re
import idna
import logging
import collections
from lxml.html import clean
from lxml import etree

from email.header import decode_header, Header
from email.utils import getaddresses
from app.mail.tools import misc, pycompat

_logger = logging.getLogger(__name__)


# ----------------------------------------------------------
# HTML Sanitizer
# ----------------------------------------------------------

tags_to_kill = ['base', 'embed', 'frame', 'head', 'iframe', 'link', 'meta',
                'noscript', 'object', 'script', 'style', 'title']

tags_to_remove = ['html', 'body']

# allow new semantic HTML5 tags
allowed_tags = clean.defs.tags | frozenset(
    'article bdi section header footer hgroup nav aside figure main'.split() + [etree.Comment])
safe_attrs = clean.defs.safe_attrs | frozenset(
    ['style',
     'data-o-mail-quote',  # quote detection
     'data-oe-model', 'data-oe-id', 'data-oe-field', 'data-oe-type', 'data-oe-expression', 'data-oe-translation-id', 'data-oe-nodeid',
     'data-publish', 'data-id', 'data-res_id', 'data-interval', 'data-member_id', 'data-scroll-background-ratio', 'data-view-id',
     ])

mail_header_msgid_re = re.compile('<[^<>]+>')


email_addr_escapes_re = re.compile(r'[\\"]')
COMMASPACE = ', '
LOG_NOTSET = 'notset'
LOG_DEBUG = 'debug'
LOG_INFO = 'info'
LOG_WARNING = 'warn'
LOG_ERROR = 'error'
LOG_CRITICAL = 'critical'


# TODO get_encodings, ustr and exception_to_unicode were originally from tools.misc.
# There are here until we refactor tools so that this module doesn't depends on tools.


def get_encodings(hint_encoding='utf-8'):
    fallbacks = {
        'latin1': 'latin9',
        'iso-8859-1': 'iso8859-15',
        'cp1252': '1252',
    }
    if hint_encoding:
        yield hint_encoding
        if hint_encoding.lower() in fallbacks:
            yield fallbacks[hint_encoding.lower()]

    # some defaults (also taking care of pure ASCII)
    for charset in ['utf8', 'latin1']:
        if not hint_encoding or (charset.lower() != hint_encoding.lower()):
            yield charset

    from locale import getpreferredencoding
    prefenc = getpreferredencoding()
    if prefenc and prefenc.lower() != 'utf-8':
        yield prefenc
        prefenc = fallbacks.get(prefenc.lower())
        if prefenc:
            yield prefenc


def decode_smtp_header(smtp_header):
    """
    Returns unicode() string conversion of the given encoded smtp header
    text. email.header decode_header method returns a decoded string and its
    charset for each deocded part of the header. This message unicodes the 
    decoded header and join them in a complete string.
    """
    if isinstance(smtp_header, Header):
        smtp_header = ustr(smtp_header)
    if smtp_header:
        text = decode_header(smtp_header.replace('\r', ''))
        # The joining space will not be needed as of python 3.3
        # See https://github.com/python/cpython/commit/07ea53cb218812404cdbde820647ce6e4b2d0f8e
        sep = ' ' if pycompat.PY2 else ''
        return sep.join([ustr(x[0], x[1]) for x in text])
    return u''


def decode_message_header(message, header, separator=' '):
    return separator.join(h for h in message.get_all(header, []) if h)


def email_split_tuples(text):
    """Return a list of (name, email) addresse tuples found in ```text```"""
    if not text:
        return []
    return [(addr[0], addr[1]) for addr in getaddresses([text])
            # getaddresses() returns '' when email parsing fails, and
            # sometimes returns emails without at least '@'. The '@'
            # is strictly required in RFC2822's `addr-spec`.
            if addr[1]
            if '@' in addr[1]]


def email_split_and_format(text):
    """Return a list of email addresses found in ```text```, formatted using formataddr."""
    if not text:
        return []
    return [formataddr((name, email)) for (name, email) in email_split_tuples(text)]


def formataddr(pair, charset='utf-8'):
    """Pretty format a 2-tuple of the form (realname, email_address).

    If the first element of a pair is falsy then only the email address
    is returned.

    Set the charset to ascii to get a RFC-2822 complaint email. The realname
    will be base64 encoded (if necessary) and the domain part of the email will
    be punycode encoded (if necessary). The local part is left unchanged thus
    require the SMTPUTF8 extension when there are non-ascii characters.

    >>> formataddr(('John Doe', 'johndoe@example.com'))
    '"John Doe" <johndoe@example.com>'

    >>> formataddr(('', 'johndoe@example.com'))
    'johndoe@example.com'
    """
    name, address = pair
    local, _, domain = address.rpartition('@')

    try:
        domain.encode(charset)
    except UnicodeEncodeError:
        # rfc5890 - Internationalized Domain Names for Applications (IDNA)
        domain = idna.encode(domain).decode('ascii')

    if name:
        try:
            name.encode(charset)
        except UnicodeEncodeError:
            # charset mismatch, encode as utf-8/base64
            # rfc2047 - MIME Message Header Extensions for Non-ASCII Text
            name = base64.b64encode(name.encode('utf-8')).decode('ascii')
            return f"=?utf-8?b?{name}?= <{local}@{domain}>"
        else:
            # ascii name, escape it if needed
            # rfc2822 - Internet Message Format
            # #section-3.4 - Address Specification
            name = email_addr_escapes_re.sub(r'\\\g<0>', name)
            return f'"{name}" <{local}@{domain}>'
    return f"{local}@{domain}"


text_type = type(u'')


def ustr(value, hint_encoding='utf-8', errors='strict'):
    """This method is similar to the builtin `unicode`, except 
    that it may try multiple encodings to find one that works
    for decoding `value`, and defaults to 'utf-8' first.

    :param value: the value to convert
    :param hint_encoding: an optional encoding that was detected
        upstream and should be tried first to decode ``value``.
    :param str errors: optional `errors` flag to pass to the unicode
        built-in to indicate how illegal character values should be 
        treated when converting a string: 'strict', 'ignore' or 'replace'
        (see ``unicode()`` constructor).
        Passing anything other than 'strict' means that the first
        encoding tried will be used, even if it's not the correct
        one to use, so be careful! Ignored if value is not a string/unicode/
    :raise: UnicodeError if value cannot be coerced to unicode
    :return: Unicode string representing the given value
    """

    # We use direct type comparison instead of `isinstance`
    # as much as possible, in order to make the most common
    # cases faster (isinstance/issubclass are significantly slower)
    ttype = type(value)

    if ttype is text_type:
        return value

    # special short-circuit for str, as we still need to support
    if ttype is bytes or issubclass(ttype, bytes):

        # try hint_encoding first, avoids call to get_encoding()
        # for the most common case
        try:
            return value.decode(hint_encoding, errors=errors)
        except Exception:
            pass

        # rare: no luck with hint_encoding, attempt other ones
        for ln in get_encodings(hint_encoding):
            try:
                return value.decode(ln, errors=errors)
            except Exception:
                pass

    if isinstance(value, Exception):
        return exception_to_unicode(value)

    # fallback for non-string values
    try:
        return text_type(value)
    except Exception:
        raise UnicodeError('unable to convert %r' % (value))


def exception_to_unicode(e):
    if getattr(e, 'args', ()):
        return "\n".join((ustr(a) for a in e.args))
    try:
        return text_type(e)
    except Exception:
        return u"Unknown message"


def html_keep_url(text):
    """ Transform the url into clickable link with <a/> tag """
    idx = 0
    final = ''
    link_tags = re.compile(
        r"""(?<!["'])((ftp|http|https):\/\/(\w+:{0,1}\w*@)?([^\s<"']+)(:[0-9]+)?(\/|\/([^\s<"']))?)(?![^\s<"']*["']|[^\s<"']*</a>)""")
    for item in re.finditer(link_tags, text):
        final += text[idx:item.start()]
        final += '<a href="%s" target="_blank" rel="noreferrer noopener">%s</a>' % (
            item.group(0), item.group(0))
        idx = item.end()
    final += text[idx:]
    return final


def plaintext2html(text, container_tag=False):
    """ Convert plaintext into html. Content of the text is escaped to manage
        html entities, using misc.html_escape().
        - all \n,\r are replaced by <br />
        - enclose content into <p>
        - convert url into clickable link
        - 2 or more consecutive <br /> are considered as paragraph breaks

        :param string container_tag: container of the html; by default the
            content is embedded into a <div>
    """
    text = misc.html_escape(ustr(text))

    # 1. replace \n and \r
    text = text.replace('\n', '<br/>')
    text = text.replace('\r', '<br/>')

    # 2. clickable links
    text = html_keep_url(text)

    # 3-4: form paragraphs
    idx = 0
    final = '<p>'
    br_tags = re.compile(r'(([<]\s*[bB][rR]\s*\/?[>]\s*){2,})')
    for item in re.finditer(br_tags, text):
        final += text[idx:item.start()] + '</p><p>'
        idx = item.end()
    final += text[idx:] + '</p>'

    # 5. container
    if container_tag:
        final = '<%s>%s</%s>' % (container_tag, final, container_tag)
    return ustr(final)


def append_content_to_html(html, content, plaintext=True, preserve=False, container_tag=False):
    """ Append extra content at the end of an HTML snippet, trying
        to locate the end of the HTML document (</body>, </html>, or
        EOF), and converting the provided content in html unless ``plaintext``
        is False.
        Content conversion can be done in two ways:
        - wrapping it into a pre (preserve=True)
        - use plaintext2html (preserve=False, using container_tag to wrap the
            whole content)
        A side-effect of this method is to coerce all HTML tags to
        lowercase in ``html``, and strip enclosing <html> or <body> tags in
        content if ``plaintext`` is False.

        :param str html: html tagsoup (doesn't have to be XHTML)
        :param str content: extra content to append
        :param bool plaintext: whether content is plaintext and should
            be wrapped in a <pre/> tag.
        :param bool preserve: if content is plaintext, wrap it into a <pre>
            instead of converting it into html
    """
    html = ustr(html)
    if plaintext and preserve:
        content = u'\n<pre>%s</pre>\n' % misc.html_escape(ustr(content))
    elif plaintext:
        content = '\n%s\n' % plaintext2html(content, container_tag)
    else:
        content = re.sub(
            r'(?i)(</?(?:html|body|head|!\s*DOCTYPE)[^>]*>)', '', content)
        content = u'\n%s\n' % ustr(content)
    # Force all tags to lowercase
    html = re.sub(r'(</?)(\w+)([ >])',
                  lambda m: '%s%s%s' % (m.group(1), m.group(2).lower(), m.group(3)), html)
    insert_location = html.find('</body>')
    if insert_location == -1:
        insert_location = html.find('</html>')
    if insert_location == -1:
        return '%s%s' % (html, content)
    return '%s%s%s' % (html[:insert_location], content, html[insert_location:])


class _Cleaner(clean.Cleaner):

    _style_re = re.compile(
        r'''([\w-]+)\s*:\s*((?:[^;"']|"[^";]*"|'[^';]*')+)''')

    _style_whitelist = [
        'font-size', 'font-family', 'font-weight', 'background-color', 'color', 'text-align',
        'line-height', 'letter-spacing', 'text-transform', 'text-decoration', 'opacity',
        'float', 'vertical-align', 'display',
        'padding', 'padding-top', 'padding-left', 'padding-bottom', 'padding-right',
        'margin', 'margin-top', 'margin-left', 'margin-bottom', 'margin-right',
        'white-space',
        # box model
        'border', 'border-color', 'border-radius', 'border-style', 'border-width', 'border-top', 'border-bottom',
        'height', 'width', 'max-width', 'min-width', 'min-height',
        # tables
        'border-collapse', 'border-spacing', 'caption-side', 'empty-cells', 'table-layout']

    _style_whitelist.extend(
        ['border-%s-%s' % (position, attribute)
            for position in ['top', 'bottom', 'left', 'right']
            for attribute in ('style', 'color', 'width', 'left-radius', 'right-radius')]
    )

    strip_classes = False
    sanitize_style = False

    def __call__(self, doc):
        # perform quote detection before cleaning and class removal
        for el in doc.iter(tag=etree.Element):
            self.tag_quote(el)

        super(_Cleaner, self).__call__(doc)

        # if we keep attributes but still remove classes
        if not getattr(self, 'safe_attrs_only', False) and self.strip_classes:
            for el in doc.iter(tag=etree.Element):
                self.strip_class(el)

        # if we keep style attribute, sanitize them
        if not self.style and self.sanitize_style:
            for el in doc.iter(tag=etree.Element):
                self.parse_style(el)

    def tag_quote(self, el):
        def _create_new_node(tag, text, tail=None, attrs=None):
            new_node = etree.Element(tag)
            new_node.text = text
            new_node.tail = tail
            if attrs:
                for key, val in attrs.items():
                    new_node.set(key, val)
            return new_node

        def _tag_matching_regex_in_text(regex, node, tag='span', attrs=None):
            text = node.text or ''
            if not re.search(regex, text):
                return

            child_node = None
            idx, node_idx = 0, 0
            for item in re.finditer(regex, text):
                new_node = _create_new_node(
                    tag, text[item.start():item.end()], None, attrs)
                if child_node is None:
                    node.text = text[idx:item.start()]
                    new_node.tail = text[item.end():]
                    node.insert(node_idx, new_node)
                else:
                    child_node.tail = text[idx:item.start()]
                    new_node.tail = text[item.end():]
                    node.insert(node_idx, new_node)
                child_node = new_node
                idx = item.end()
                node_idx = node_idx + 1

        el_class = el.get('class', '') or ''
        el_id = el.get('id', '') or ''

        # gmail or yahoo // # outlook, html // # msoffice
        if ('gmail_extra' in el_class or 'yahoo_quoted' in el_class) or \
                (el.tag == 'hr' and ('stopSpelling' in el_class or 'stopSpelling' in el_id)) or \
                ('SkyDrivePlaceholder' in el_class or 'SkyDrivePlaceholder' in el_class):
            el.set('data-o-mail-quote', '1')
            if el.getparent() is not None:
                el.getparent().set('data-o-mail-quote-container', '1')

        # html signature (-- <br />blah)
        signature_begin = re.compile(r"((?:(?:^|\n)[-]{2}[\s]?$))")
        if el.text and el.find('br') is not None and re.search(signature_begin, el.text):
            el.set('data-o-mail-quote', '1')
            if el.getparent() is not None:
                el.getparent().set('data-o-mail-quote-container', '1')

        # text-based quotes (>, >>) and signatures (-- Signature)
        text_complete_regex = re.compile(
            r"((?:\n[>]+[^\n\r]*)+|(?:(?:^|\n)[-]{2}[\s]?[\r\n]{1,2}[\s\S]+))")
        if not el.get('data-o-mail-quote'):
            _tag_matching_regex_in_text(text_complete_regex, el, 'span', {
                                        'data-o-mail-quote': '1'})

        if el.tag == 'blockquote':
            # remove single node
            el.set('data-o-mail-quote-node', '1')
            el.set('data-o-mail-quote', '1')
        if el.getparent() is not None and (el.getparent().get('data-o-mail-quote') or el.getparent().get('data-o-mail-quote-container')) and not el.getparent().get('data-o-mail-quote-node'):
            el.set('data-o-mail-quote', '1')

    def strip_class(self, el):
        if el.attrib.get('class'):
            del el.attrib['class']

    def parse_style(self, el):
        attributes = el.attrib
        styling = attributes.get('style')
        if styling:
            valid_styles = collections.OrderedDict()
            styles = self._style_re.findall(styling)
            for style in styles:
                if style[0].lower() in self._style_whitelist:
                    valid_styles[style[0].lower()] = style[1]
            if valid_styles:
                el.attrib['style'] = '; '.join('%s:%s' % (
                    key, val) for (key, val) in valid_styles.items())
            else:
                del el.attrib['style']


def html_sanitize(src, silent=True, sanitize_tags=True, sanitize_attributes=False, sanitize_style=False, sanitize_form=True, strip_style=False, strip_classes=False):
    if not src:
        return src
    src = ustr(src, errors='replace')
    # html: remove encoding attribute inside tags
    doctype = re.compile(
        r'(<[^>]*\s)(encoding=(["\'][^"\']*?["\']|[^\s\n\r>]+)(\s[^>]*|/)?>)', re.IGNORECASE | re.DOTALL)
    src = doctype.sub(u"", src)

    logger = logging.getLogger(__name__ + '.html_sanitize')

    # html encode mako tags <% ... %> to decode them later and keep them alive, otherwise they are stripped by the cleaner
    src = src.replace(u'<%', misc.html_escape(u'<%'))
    src = src.replace(u'%>', misc.html_escape(u'%>'))

    kwargs = {
        'page_structure': True,
        'style': strip_style,              # True = remove style tags/attrs
        'sanitize_style': sanitize_style,  # True = sanitize styling
        'forms': sanitize_form,            # True = remove form tags
        'remove_unknown_tags': False,
        'comments': False,
        'processing_instructions': False
    }
    if sanitize_tags:
        kwargs['allow_tags'] = allowed_tags
        if etree.LXML_VERSION >= (2, 3, 1):
            # kill_tags attribute has been added in version 2.3.1
            kwargs.update({
                'kill_tags': tags_to_kill,
                'remove_tags': tags_to_remove,
            })
        else:
            kwargs['remove_tags'] = tags_to_kill + tags_to_remove

    # lxml < 3.1.0 does not allow to specify safe_attrs. We keep all attributes in order to keep "style"
    if sanitize_attributes and etree.LXML_VERSION >= (3, 1, 0):
        if strip_classes:
            current_safe_attrs = safe_attrs - frozenset(['class'])
        else:
            current_safe_attrs = safe_attrs
        kwargs.update({
            'safe_attrs_only': True,
            'safe_attrs': current_safe_attrs,
        })
    else:
        kwargs.update({
            'safe_attrs_only': False,  # keep oe-data attributes + style
            # remove classes, even when keeping other attributes
            'strip_classes': strip_classes,
        })

    try:
        # some corner cases make the parser crash (such as <SCRIPT/XSS SRC=\"http://ha.ckers.org/xss.js\"></SCRIPT> in test_mail)
        cleaner = _Cleaner(**kwargs)
        cleaned = cleaner.clean_html(src)
        assert isinstance(cleaned, str)
        # MAKO compatibility: $, { and } inside quotes are escaped, preventing correct mako execution
        cleaned = cleaned.replace(u'%24', u'$')
        cleaned = cleaned.replace(u'%7B', u'{')
        cleaned = cleaned.replace(u'%7D', u'}')
        cleaned = cleaned.replace(u'%20', u' ')
        cleaned = cleaned.replace(u'%5B', u'[')
        cleaned = cleaned.replace(u'%5D', u']')
        cleaned = cleaned.replace(u'%7C', u'|')
        cleaned = cleaned.replace(u'&lt;%', u'<%')
        cleaned = cleaned.replace(u'%&gt;', u'%>')
        # html considerations so real html content match database value
        cleaned.replace(u'\xa0', u'&nbsp;')
    except etree.ParserError as e:
        if 'empty' in str(e):
            return u""
        if not silent:
            raise
        logger.warning(
            u'ParserError obtained when sanitizing %r', src, exc_info=True)
        cleaned = u'<p>ParserError when sanitizing</p>'
    except Exception:
        if not silent:
            raise
        logger.warning(
            u'unknown error obtained when sanitizing %r', src, exc_info=True)
        cleaned = u'<p>Unknown error when sanitizing</p>'

    # this is ugly, but lxml/etree tostring want to put everything in a 'div' that breaks the editor -> remove that
    if cleaned.startswith(u'<div>') and cleaned.endswith(u'</div>'):
        cleaned = cleaned[5:-6]

    return cleaned


def email_split(text):
    """ Return a list of the email addresses found in ``text`` """
    if not text:
        return []
    return [email for (name, email) in email_split_tuples(text)]


def email_normalize(text):
    """ Sanitize and standardize email address entries.
        A normalized email is considered as :
        - having a left part + @ + a right part (the domain can be without '.something')
        - being lower case
        - having no name before the address. Typically, having no 'Name <>'
        Ex:
        - Possible Input Email : 'Name <NaMe@DoMaIn.CoM>'
        - Normalized Output Email : 'name@domain.com'
    """
    emails = email_split(text)
    if not emails or len(emails) != 1:
        return False
    return emails[0].lower()
