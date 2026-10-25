FROM alpine:3.20

RUN apk add --no-cache tinyproxy \
    && mkdir -p /var/log/tinyproxy /run/tinyproxy \
    && chown -R tinyproxy:tinyproxy /var/log/tinyproxy /run/tinyproxy

COPY tinyproxy.conf /etc/tinyproxy/tinyproxy.conf

EXPOSE 8888

USER tinyproxy
CMD ["tinyproxy", "-d", "-c", "/etc/tinyproxy/tinyproxy.conf"]
