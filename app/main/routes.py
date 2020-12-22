from flask import render_template, url_for, redirect
from app.main import bp


@bp.route('/', methods=['GET', 'POST'])
def index():
    # return redirect(url_for('crm.kanban'))
    return render_template('index.html', title='Open Source Business Apps')
