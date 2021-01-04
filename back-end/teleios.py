from app import create_app, db, cli
from app.auth.models.user import User
from flask import url_for
from datetime import datetime
from app.auth.models.user import User

app = create_app()
cli.register(app)


@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User}


@app.cli.command()
def fetchmail():
    """Scheduled job for fetching incoming emails."""
    print(str(datetime.utcnow()), 'Fetching emails')
    print(url_for('fetchmail.fetchmail'))
    # user = User(fname='Alfred')
    # db.session.add(user)
    # db.session.commit()
    # return url_for('fetchmail.fetchmail')
    return "success"