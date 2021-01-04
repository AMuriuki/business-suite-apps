#-*- coding:utf-8 -*-
# Part of Teleios. See LICENSE file for full copyright and licensing details.

from flask import url_for, render_template
from app.settings import bp

@bp.route('/settings', methods=['GET', 'POST'])
def settings():
    return render_template('settings/settings.html', title='Settings | Teleios')
