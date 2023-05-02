FROM python

RUN mkdir /app

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

COPY . .

CMD [ "python", "manage.py" , "runserver", "0.0.0.0:8000"]