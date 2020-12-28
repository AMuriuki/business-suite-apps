import werkzeug
import werkzeug.utils


def html_escape(text):
    return werkzeug.utils.escape(text)
