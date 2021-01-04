#!/usr/bin/env python3

import os
import time
from flask import render_template, redirect, url_for, flash, request
from werkzeug.urls import url_parse
from flask_babel import _
from app import db
from app.fetchmail import bp
from app.fetchmail.models.fetchmail import FetchmailServer


@bp.route('/fetchmail', methods=['GET', 'POST'])
def fetchmail():
    print("Fetching mail")
    mailserver = db.session.query(FetchmailServer).first()
    print(mailserver)
    FetchmailServer.fetch_mail(mailserver)


# schedule.every(0.1).minutes.do(url_for('fetchmail.fetchmail'))
# while True:
#     schedule.run_pending()
