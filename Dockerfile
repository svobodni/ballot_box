FROM python:2

COPY ./requirements_docker.txt /app/requirements.txt

WORKDIR /app

RUN pip install -r requirements.txt

COPY . /app

ENTRYPOINT [ "python2" ]

CMD [ "runserver.py" ]
