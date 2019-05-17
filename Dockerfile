FROM python:2.7.16-alpine

ADD  requirements.txt /tmp
RUN pip install -r /tmp/requirements.txt -i https://mirrors.aliyun.com/pypi/simple

ADD . /code
WORKDIR /code
ENTRYPOINT [ "/bin/sh",  "entrypoints.sh"]

