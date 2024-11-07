FROM docker:dind-rootless

RUN apt update && apt install -y python3 python3-pip

WORKDIR app

COPY requirements.txt .
COPY main.py .

RUN pip install -r requirements.txt

CMD ["python", "main.py"]