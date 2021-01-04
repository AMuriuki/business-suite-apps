# -*- coding:utf-8 -*-
# Part of Teleios. See LICENSE file for full copyright and licensing details.

from flask import url_for, render_template
from flask_login import login_required
from app.settings import bp
from app.decorators import admin_required


@bp.route('/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def settings():
    return render_template('settings/settings.html', title='Settings | Teleios')
