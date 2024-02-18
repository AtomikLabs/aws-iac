FROM public.ecr.aws/lambda/python:3.9
WORKDIR /var/task
COPY services/fetch_daily_summaries/requirements.txt requirements.txt
COPY services/fetch_daily_summaries/requirements.docker.txt requirements.docker.txt
RUN python -m pip install -r requirements.docker.txt
COPY services/fetch_daily_summaries/src .
CMD ["fetch_daily_summaries.lambda_handler"]