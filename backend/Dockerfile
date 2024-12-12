FROM python:3.11.7

RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY ./requirements.txt requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY ./main.py main.py 
COPY ./settings.py settings.py

# VOLUME ./models/ models
# VOLUME ./logs/ logs

EXPOSE 8003

# CMD [ "python", "main.py", "0.0.0.0", "8003" ]
CMD [ "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003" ]