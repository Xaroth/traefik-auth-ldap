from werkzeug.middleware.proxy_fix import ProxyFix as BaseProxyFix


class ProxyFix(BaseProxyFix):
    def __init__(self, app, num_proxies):
        super().__init__(app, x_for=num_proxies, x_proto=num_proxies, x_host=num_proxies, x_port=num_proxies, x_prefix=num_proxies)
