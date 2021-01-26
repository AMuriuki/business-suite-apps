from app import create_app, db, cli
from app.auth.models.user import User
from flask import url_for
from datetime import datetime
from app.auth.models.user import User, Role
from flask_migrate import Migrate, upgrade

app = create_app()
cli.register(app)


@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User}


@app.cli.command()
def fetchmail():
    """Scheduled job for fetching incoming emails."""
    print(str(datetime.utcnow()), 'Fetching emails')
    # user = User(fname='Alfred')
    # db.session.add(user)
    # db.session.commit()
    # return url_for('fetchmail.fetchmail')
    return "success"


@app.cli.command()
def deploy():
    """Run deployment tasks."""
    # migrate database to latest revision
    upgrade()

    # create or update user roles
    Role.insert_roles()
    User.dummy_users()  
