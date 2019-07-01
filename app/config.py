import os
from os.path import exists

from jinja2 import Environment, BaseLoader


def to_bool(x):
    if isinstance(x, str):
        x = x.lower()
    return x in ("1", "true", "yes", "y", 1, True)


def domain_to_dn(domain):
    return ','.join(["dc=%s" % x for x in domain.split('.')])


def replace(x, **kwargs):
    if isinstance(x, list):
        return [replace(y, **kwargs) for y in x]
    else:
        template = Environment(loader=BaseLoader()).from_string(x)
        return template.render(**kwargs)


def kv_list(x):
    if isinstance(x, list):
        return [kv_list(y) for y in x]
    else:
        k, _, v = x.partition("=")
        return k, v


def from_environ(name, default=None, allow_secret=True, is_list=False, is_number=False, is_bool=False, required=False):
    name = name.upper()
    value = None

    if allow_secret:
        value = os.environ.get("%s_FILE" % name, None)
        if value and exists(value):
            print("Loading setting '%s' from file '%s'" % (name, value))
            with open(value, "r", encoding="utf-8") as fh:
                value = fh.read()
    
    if not value:
        value = os.environ.get(name, None)

    if not value and required:
        raise Exception("Required environmetn variable '%s' not set" % name)

    if not value:
        return default
    orig_value = value

    if is_list:
        sep = "," if is_list is True else is_list
        value = value.split(sep)

    if is_number:
        if is_list:
            try:
                value = [int(x) for x in value]
            except ValueError:
                raise Exception("Value '%s' for '%s' is not a list of numbers" % (orig_value, name))
        else:
            try:
                value = int(value)
            except ValueError:
                raise Exception("Value '%s' for '%s' is not a number" % (orig_value, name))
    elif is_bool:
        if is_list:
            try:
                value = [to_bool(x) for x in value]
            except ValueError:
                raise Exception("Value '%s' for '%s' is not a list of booleans" % (orig_value, name))
        else:
            try:
                value = to_bool(value)
            except ValueError:
                raise Exception("Value '%s' for '%s' is not a boolean" % (orig_value, name))
   
    return value


class Config:
    SECRET_KEY = from_environ("SECRET_KEY", os.urandom(16).decode("utf-8", errors="ignore")).encode("utf-8")

    NUMBER_OF_PROXIES = from_environ("NUMBER_OF_PROXIES", 1, is_number=True)

    CACHE_TYPE = from_environ("CACHE_TYPE", "simple")
    CACHE_UWSGI_NAME = from_environ("CACHE_NAME", "app")
    CACHE_DEFAULT_TIMEOUT = from_environ("CACHE_DEFAULT_TIMEOUT", 300, is_number=True)

    AUTH_GROUP_REQUIRED = from_environ("AUTH_GROUP_REQUIRED", [], is_list=True)
    AUTH_GROUP_PER_DOMAIN = kv_list(from_environ("AUTH_GROUP_PER_DOMAIN", [], is_list=True))

    SESSION_COOKIE_DOMAIN = AUTH_COOKIE_DOMAIN = from_environ("AUTH_COOKIE_DOMAIN", "example.com")

    SESSION_REFRESH_EACH_REQUEST = True
    SESSION_COOKIE_SECURE = AUTH_COOKIE_SECURE = from_environ("AUTH_COOKIE_SECURE", False, is_bool=True)
    SESSION_COOKIE_HTTPONLY = AUTH_COOKIE_PATH = from_environ("AUTH_COOKIE_PATH", True, is_bool=True)
    SESSION_COOKIE_PATH = AUTH_COOKIE_PATH = from_environ("AUTH_COOKIE_PATH", "/")
    SESSION_COOKIE_NAME = AUTH_COOKIE_NAME = from_environ("AUTH_COOKIE_NAME", "sso-session")

    AUTH_LOGIN_DOMAIN = from_environ("AUTH_LOGIN_DOMAIN", required=True)
    AUTH_LOGIN_TLS = "https" if from_environ("AUTH_LOGIN_TLS", default=True, is_bool=True) else "http"

    LDAP_WAIT_AVAILABLE = from_environ("LDAP_WAIT_AVAILABLE", -1, is_number=True)

    LDAP_TLS = from_environ("LDAP_TLS", True, is_bool=True)
    LDAP_TLS_SNI = from_environ("LDAP_TLS_SNI", True, is_bool=True)
    LDAP_TLS_VERIFY = from_environ("LDAP_TLS_VERIFY", True, is_bool=True)
    # LDAP_HOSTNAME will be used for SNI
    LDAP_HOSTNAME = from_environ("LDAP_HOSTNAME", "openldap")
    LDAP_SCHEME = from_environ("LDAP_SCHEME", "ldaps" if LDAP_TLS else "ldap")
    LDAP_PORT = from_environ("LDAP_PORT", 636 if LDAP_TLS else 389)
    LDAP_URI = replace(from_environ("LDAP_URI", "{{ LDAP_SCHEME }}://{{ LDAP_HOSTNAME }}:{{ LDAP_PORT }}"), LDAP_SCHEME=LDAP_SCHEME, LDAP_HOSTNAME=LDAP_HOSTNAME, LDAP_PORT=LDAP_PORT)

    LDAP_DOMAIN = from_environ("LDAP_DOMAIN", "example.com")
    LDAP_BASE_DN = from_environ("LDAP_BASE_DN", domain_to_dn(LDAP_DOMAIN))
    LDAP_USER_BASE_DN = replace(from_environ("LDAP_USER_BASE_DN", ["ou=people,{{ LDAP_BASE_DN }}"], is_list=True), LDAP_BASE_DN=LDAP_BASE_DN)
    # LDAP_GROUP_BASE_DN = replace(from_environ("LDAP_GROUP_BASE_DN", ["ou=groups,{{ LDAP_BASE_DN }}"], is_list=True), LDAP_BASE_DN=LDAP_BASE_DN)

    LDAP_USERNAME_ATTR = from_environ("LDAP_USERNAME_ATTR", "uid")
    LDAP_GROUP_ATTR = from_environ("LDAP_GROUP_ATTR", "memberOf")
    LDAP_GROUP_NAME_ATTR = from_environ("LDAP_GROUP_NAME_ATTR", "cn")

    LDAP_LAST_SET_ATTR = from_environ("LDAP_LAST_SET_ATTR", ["sambaPwdLastSet", "shadowLastChange"], is_list=True)

    LDAP_BIND_DN = replace(from_environ("LDAP_BIND_DN", "cn=readonly,{{ LDAP_BASE_DN }}"), LDAP_USER_BASE_DN=LDAP_USER_BASE_DN, LDAP_BASE_DN=LDAP_BASE_DN)
    LDAP_BIND_PASSWORD = from_environ("LDAP_BIND_PASSWORD")

    LDAP_USER_FILTER = replace(from_environ("LDAP_USER_FILTER", "(&({{ LDAP_USERNAME_ATTR}}=%s)(|(objectClass=posixAccount)(objectClass=sambaSAMAccount)))"), LDAP_USERNAME_ATTR=LDAP_USERNAME_ATTR)
    
    # ldap-attr@header,ldap-attr@header
    # TODO
    RETURN_HEADERS = from_environ("RETURN_HEADERS", ["%s@x-username" % LDAP_USERNAME_ATTR, "mail@x-email", "uidNumber@x-uid", "gidNumber@x-gid"], is_list=True)
