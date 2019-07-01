FROM alpine:latest
LABEL author="https://github.com/Xaroth"

COPY requirements.txt /tmp/requirements.txt

RUN apk add --no-cache python3 bash uwsgi uwsgi-python3 supervisor nginx && \
    python3 -m ensurepip && \
    rm -rf /usr/lib/python*/ensurepip && \
    pip3 install --upgrade pip setuptools wheel && \
    pip3 install -r /tmp/requirements.txt && \
    rm -r /root/.cache

COPY nginx.conf /etc/nginx/
COPY uwsgi.ini /etc/uwsgi/
COPY supervisord.conf /etc/supervisord.conf

COPY ./app /application/app
COPY ./static /application/static
COPY ./templates /application/templates

RUN chown -R :nginx /application && chmod -R g+r /application

WORKDIR /application

CMD ["/usr/bin/supervisord"]
