FROM python:3

RUN mkdir /src
WORKDIR /src

RUN pip install openshift
COPY terminator.py /usr/local/bin/terminator

ENTRYPOINT ["python", "/usr/local/bin/terminator"]

