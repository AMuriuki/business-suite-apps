from flask import render_template, redirect, url_for, flash, request
from werkzeug.urls import url_parse
from flask_babel import _
from app import db
from app.fetchmail import bp
from app.fetchmail.models.fetchmail import FetchmailServer


@bp.route('/fetchmail', methods=['GET', 'POST'])
def fetchmail():
    mailserver = db.session.query(FetchmailServer).first()
    FetchmailServer.fetch_mail(mailserver)      
    return "success"
