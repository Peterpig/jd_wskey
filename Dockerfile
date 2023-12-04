# syntax = docker/dockerfile:experimental
FROM python:3
WORKDIR /app
COPY . .

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt 

CMD ["python", "jd_tg_monitor.py"]
