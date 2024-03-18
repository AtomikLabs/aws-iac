FROM public.ecr.aws/lambda/python:3.9
WORKDIR /var/task

COPY services/prototype/src/requirements.txt .
COPY services/prototype/src/requirements.docker.txt .

RUN python -m pip install -r requirements.docker.txt
COPY services/prototype/src/prototype ./prototype

CMD ["prototype.lambda_handler.lambda_handler"]