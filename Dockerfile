FROM python:3.11-slim

WORKDIR /app

RUN pip install kafka-python msgpack snakeviz matplotlib

COPY python-files/ /app/

CMD ["python", "-u", "run_generators.py"]