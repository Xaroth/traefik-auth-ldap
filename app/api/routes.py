from urllib.parse import urlsplit, urlunsplit

from flask import request, abort, current_app, redirect, session
from flask import url_for as base_url_for
from flask_login import current_user

from app.api import bp

LOGIN_DOMAIN_PARTS = urlsplit("//%s" % current_app.config["AUTH_LOGIN_DOMAIN"], scheme=current_app.config["AUTH_LOGIN_TLS"], allow_fragments=True)


def url_for(*args, **kwargs):
    external = kwargs.pop("_external")
    url = base_url_for(*args, **kwargs)
    if external:
        parts = urlsplit(url, scheme=current_app.config["AUTH_LOGIN_TLS"], allow_fragments=True)
        url = urlunsplit(LOGIN_DOMAIN_PARTS[:2] + parts[2:])
    return url


def get_required_groups():
    groups = []
    if current_app.config["AUTH_GROUP_REQUIRED"]:
        groups.extend(current_app.config["AUTH_GROUP_REQUIRED"])
    forward_groups = request.args.get("required_groups")
    if forward_groups:
        groups.extend(forward_groups.split(','))
    if current_app.config["AUTH_GROUP_PER_DOMAIN"]:
        current_host = request.host.lower()
        groups.extend([group for domain, group in current_app.config["AUTH_GROUP_PER_DOMAIN"] if domain.lower() == current_host])
    
    return set(groups)

def get_original_url():
    scheme = request.headers.get("X-Forwarded-Proto", "https")
    netloc = request.headers.get("X-Forwarded-Host")
    port = request.headers.get("X-Forwarded-Port", '443')
    try:
        port = int(port)
    except:
        port = None
    if (scheme, port) in (("https", 443), ("http", 80)):
        port = None
    if port:
        netloc = "%s:%d" % (netloc, port)
    parts = urlsplit(request.headers.get("X-Forwarded-Uri", "/"))
    url = urlunsplit((scheme, netloc) + parts[2:])
    print(url)
    return url


@bp.route("/auth")
def auth():
    if current_user.is_authenticated:
        current_groups = set(current_user.groups)
        required_groups = get_required_groups()
        if not required_groups.difference(current_groups):
            return ''

    return redirect(url_for("web.login", next=get_original_url(), _external=True))
