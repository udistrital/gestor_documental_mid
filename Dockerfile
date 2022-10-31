FROM python:3.7

RUN pip install awscli

COPY entrypoint.sh entrypoint.sh

RUN chmod +x entrypoint.sh

RUN mkdir documents

RUN touch ./documents/document.pdf

ENTRYPOINT ["/entrypoint.sh"]

ADD requirements.txt .

RUN pip install -r requirements.txt

ADD api.py .

#CMD [ "python", "./api.py" ]