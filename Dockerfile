FROM python:3

ADD requirements.txt .

RUN pip install requirements.txt

ADD api.py .

CMD [ "python", "./api.py" ]