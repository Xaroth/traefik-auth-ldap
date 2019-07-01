from os.path import abspath, dirname, join 
import sys
import string
import random

ROOT_DIR = abspath(dirname(dirname(__file__)))
sys.path.append(ROOT_DIR)

from flask import Flask, session
from flask_login import LoginManager
from flask_caching import Cache
from app.proxy import ProxyFix
from app.config import Config
from app.ldap import LdapManager


class FlaskApp(Flask):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ldap = None
        self.log_exception = None
        self.cache = None
        self.jinja_env.globals['csrf_token'] = self.generate_csrf_token

    def init_ldap(self):
        self.ldap = LdapManager()
        self.ldap.init_app(self)

    def init_login(self):
        self.login_manager = LoginManager()
        self.login_manager.init_app(self)

    def init_cache(self):
        self.cache = Cache()
        self.cache.init_app(self)

    def generate_csrf_token(self):
        if '_csrf_topken' not in session:
            session['_csrf_token'] = ''.join(random.choice(string.ascii_lowercase) for i in range(64))
        return session['_csrf_token']


def create_app(config_class=Config):
    app = FlaskApp(__name__,
                   template_folder=join(ROOT_DIR, 'templates'),
                   static_folder=join(ROOT_DIR, 'static'),
                   )
    app.config.from_object(config_class)
    app.config.from_envvar("APPLICATION_SETTINGS", silent=True)
    
    with app.app_context():
        app.init_login()
        app.init_ldap()
        app.init_cache()

    with app.app_context():        
        from app.user import User
        from app.api import bp as bp_api
        from app.web import bp as bp_web

        app.register_blueprint(bp_api)
        app.register_blueprint(bp_web)

    app.wsgi_app = ProxyFix(app.wsgi_app, app.config["NUMBER_OF_PROXIES"])
    app.configured = True

    return app
