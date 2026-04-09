FROM python:3.11-slim

WORKDIR /app

RUN pip install kafka-python msgpack

# Hier laden wir nun den sauberen Ordner in den Container
COPY python-files/ /app/

CMD ["python", "-u" "run_generators.py"]