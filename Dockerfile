FROM python:3.10-alpine

RUN apk add --no-cache tzdata supervisor

ENV TZ=Asia/Istanbul
ENV PYTHONUNBUFFERED=1
ENV DATA_DIR=/app/data
ENV RUN_MODE=loop

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY visa_slot_checker.py .
COPY supervisord.conf /etc/supervisord.conf

RUN mkdir -p /app/data /var/log

HEALTHCHECK --interval=120s --timeout=10s --start-period=90s --retries=3 \
  CMD test -s /app/data/last_success.txt || exit 1

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord.conf"]
