from flask import render_template
from app.crm import bp


@bp.route('/kanban', methods=['GET', 'POST'])
def kanban():
    return render_template('crm/kanban.html')
