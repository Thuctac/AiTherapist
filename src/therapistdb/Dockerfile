FROM python:3.11-alpine

WORKDIR /usr/src/app

# install gcc & libpq-dev for psycopg2
RUN apk add --no-cache gcc musl-dev postgresql-dev

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "init_db.py"]
