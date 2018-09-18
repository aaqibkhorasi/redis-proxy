FROM python:3

WORKDIR /opt/proxy

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 5000
CMD [ "python", "./redisProxy.py" ]
