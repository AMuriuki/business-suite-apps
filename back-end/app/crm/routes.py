from flask import render_template, redirect, url_for, flash, request
from werkzeug.urls import url_parse
from flask_babel import _
from app import db
from app.crm import bp


@bp.route('/kanban', methods=['GET', 'POST'])
def kanban():
    return render_template('crm/kanban.html', title=_('CRM | Kanban Boards'))
