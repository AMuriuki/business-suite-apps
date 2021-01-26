from datetime import datetime
from flask import render_template, flash, redirect, url_for, request, g, \
    jsonify, current_app
from flask_login import current_user, login_required
from flask_babel import _, get_locale
from guess_language import guess_language
from app import db
from app.main.forms import EditProfileForm, EmptyForm, PostForm, SearchForm, \
    MessageForm
from app.auth import models as auth_models
from app.main.models import module
from app.translate import translate
from app.main import bp
from app.decorators import admin_required


@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
@login_required
@admin_required
def index():
    _modules = module.Module
    modulecategories = module.ModuleCategory

    modulecategories = modulecategories.query.all()
    _modules = _modules.query.all()
    modules = "All apps - Categories"
    return render_template('index.html', title=_('Teleios | Home'), modules=modules, modulecategories=modulecategories, _modules=_modules)


@bp.route('/module/<name>', methods=['GET', 'POST'])
@login_required
def _module(name):
    return render_template('base.html', title=_('Teleios | '+ name))
