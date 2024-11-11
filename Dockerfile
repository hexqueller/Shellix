FROM docker:27.3.1-dind

RUN apk update && \
    apk add --no-cache python3 py3-pip

RUN python3 -m venv /opt/venv

COPY requirements.txt /app/requirements.txt
RUN /opt/venv/bin/pip install -r /app/requirements.txt

COPY main.py /app/main.py

ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

CMD ["python", "main.py"]