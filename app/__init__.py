from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bootstrap import Bootstrap
from config import Config
from flask_migrate import Migrate
import os

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'main.login'
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    Bootstrap(app)

    from . import routes
    app.register_blueprint(routes.app)

    return app
