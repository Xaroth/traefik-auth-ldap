from flask import current_app
from flask_login import login_user


class User:
    def __init__(self, dn, username, groups, unique):
        self.dn = dn
        self.username = username
        self.groups = groups
        self.unique = unique

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        unique = str(self.unique or '')
        return ':'.join([self.dn, unique])

    @classmethod
    def from_session(cls, user_id):
        cache = current_app.cache
        dn, _, current_unique = user_id.partition(':')

        data = cache.get(dn)
        if not data:
            dn, username, groups, unique = current_app.ldap.get_user_info(dn)
            cache.set(dn, [username, groups, unique])
            if not unique:
                unique = ''
            if not dn or current_unique != str(unique):
                return None
        else:
            username, groups, unique = data
            if current_unique != str(unique):
                return None
        return cls(dn, username, groups, unique)

    @classmethod
    def authenticate(cls, username, password):
        cache = current_app.cache

        dn, username, groups, unique = current_app.ldap.authenticate_user(username, password)

        if not dn:
            return None

        cache.set(dn, [username, groups, unique])
        obj = cls(dn, username, groups, unique)
        login_user(obj)
        return obj  


@current_app.login_manager.user_loader
def load_user(user_id):
    return User.from_session(user_id)
