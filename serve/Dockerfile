FROM python:3.7
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt
COPY src /app/src
ENV PYTHONPATH=/app
WORKDIR /app/


