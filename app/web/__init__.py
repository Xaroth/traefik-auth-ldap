from flask import Blueprint

bp = Blueprint('web', __name__)

from . import routes
