from ldap3 import Server, Connection, ALL, Tls, SUBTREE, BASE, ALL_ATTRIBUTES, ALL_OPERATIONAL_ATTRIBUTES
import ssl
import time

from flask import current_app


class LdapManager:
    def __init__(self):
        self.app = None
        self.config = {}
        self.ldap = None

    def create_bound_connection(self):
        return Connection(self.ldap, self.config["LDAP_BIND_DN"], self.config["LDAP_BIND_PASSWORD"], read_only=True, lazy=False)

    def test_connection(self):
        conn = self.create_bound_connection()
        try:
            conn.open()
            bound = conn.bind()
            conn.unbind()
        except Exception as e:
            current_app.logger.warning("Unable to connect to LDAP. Please check your connection settings")
            return e
        return bound

    def wait_for_connection(self, amount=-1):
        while amount != 0:
            amount -= 1
            check = self.test_connection()
            if check is True:
                current_app.logger.info("Connected to LDAP.")
                return True
            if check is False:
                current_app.logger.warning("Unable to connect to LDAP, invalid dn/password. Please check your connection settings")
                raise Exception("Error binding (is your dn/password correct?)")
            time.sleep(5)
        return check

    def init_app(self, app):
        self.app = app
        self.config = app.config
        self.tls = Tls(validate=ssl.CERT_REQUIRED if self.config["LDAP_TLS_VERIFY"] else ssl.CERT_NONE, version=ssl.PROTOCOL_TLSv1_2)
        if self.config["LDAP_TLS_SNI"]:
            self.tls.sni = self.config["LDAP_HOSTNAME"]
        self.ldap = Server(self.config["LDAP_URI"], use_ssl=self.config["LDAP_TLS"], get_info=ALL, tls=self.tls)

        online = self.wait_for_connection(self.config["LDAP_WAIT_AVAILABLE"])
        if isinstance(online, Exception):
            raise online

    def get_groups(self, *dns, group_cache=None, conn=None):
        if not conn:
            conn = self.create_bound_connection()
        if group_cache is None:
            group_cache = {}

        name_attr = self.config["LDAP_GROUP_NAME_ATTR"]
        
        with conn:
            for dn in dns:
                if dn in group_cache:
                    yield group_cache[dn]
                else:
                    conn.search(dn, "(objectClass=top)", search_scope=BASE, attributes=[name_attr])
                    if not conn.response:
                        continue
                    group_cache[conn.response[0]['dn']] = name = conn.response[0]['attributes'][name_attr][0]
                    yield name

    def _process_user(self, dn, attributes, group_cache=None, conn=None):
        membership = attributes.get(self.config["LDAP_GROUP_ATTR"], [])
        username = attributes.get(self.config["LDAP_USERNAME_ATTR"])[0]

        unique = None
        for key in self.config["LDAP_LAST_SET_ATTR"]:
            if key in attributes:
                unique = attributes[key]
                if isinstance(unique, (list, tuple)):
                    unique = unique[0]
                break

        groups = list(self.get_groups(*membership, group_cache=group_cache, conn=conn))
       
        return dn, username, groups, unique

    def get_user_info(self, dn, conn=None):
        if not conn:
            conn = self.create_bound_connection()

        group_cache = {}

        with conn:
            conn.search(dn, "(objectClass=top)", BASE, attributes=[ALL_ATTRIBUTES, ALL_OPERATIONAL_ATTRIBUTES])
            
            if not conn.response:
                return False, None, [], None

            item = conn.response[0]
            return self._process_user(item["dn"], item["attributes"], group_cache=group_cache, conn=conn)
        return False, None, [], None


    def find_user(self, username, conn=None):
        if not username:
            return
        if not conn:
            conn = self.create_bound_connection()

        user_filter = self.config["LDAP_USER_FILTER"] % username
        group_cache = {}

        with conn:
            for base in self.config["LDAP_USER_BASE_DN"]:
                conn.search(base, user_filter, SUBTREE, attributes=[ALL_ATTRIBUTES, ALL_OPERATIONAL_ATTRIBUTES])

                for item in conn.response:
                    yield self._process_user(item["dn"], item["attributes"], group_cache=group_cache, conn=conn)

    def authenticate_user(self, username, password):
        if not password:
            return False, None, [], None

        orig_username = username

        current_app.logger.info("Attempting authentication for user '%s'", orig_username)

        for dn, username, groups, unique in self.find_user(username):
            current_app.logger.debug("Trying dn: '%s'", dn)
            conn = Connection(self.ldap, dn, password, read_only=True, lazy=False)
            try:
                with conn:
                    if not conn.bound:
                        current_app.logger.debug("Failed to bind, password incorrect or invalid user")
                        continue
                    conn.search(dn, "(objectClass=top)", BASE, attributes=[self.config["LDAP_USERNAME_ATTR"]])
                    if conn.response:
                        current_app.logger.debug("Logged in as '%s'", dn)
                        return dn, username, groups, unique
            except:
                continue

        current_app.logger.info("Authentication error for user '%s'", orig_username)

        return False, None, [], None
