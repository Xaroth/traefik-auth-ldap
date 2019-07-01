from flask import request, abort, current_app, render_template, redirect, session, abort
from flask_login import current_user, logout_user

from app.web import bp
from app.user import User


@bp.before_request
def csrf_protect():
    if request.method == "POST":
        token = session.pop('_csrf_token', None)
        if not token or token != request.form.get('csrf-token'):
            abort(403)


@bp.route("/login", methods=["GET", "POST"])
def login():
    username = None
    failed = False

    next_url = request.args.get("next")

    if request.method == "POST":
        next_url = request.form.get("next")
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.authenticate(username, password)
        failed = user is None
        pass
    
    if current_user.is_authenticated and not failed:
        return redirect(next_url)

    return render_template("login.html", username=username, failed=failed, next_url=next_url)


@bp.route("/logout")
def logout():
    logout_user()
    return render_template("logout.html")
