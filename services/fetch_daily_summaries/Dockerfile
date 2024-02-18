FROM public.ecr.aws/lambda/python:3.9
WORKDIR /var/task

COPY services/fetch_daily_summaries/src/requirements.txt .
COPY services/fetch_daily_summaries/src/requirements.docker.txt .

RUN python -m pip install -r requirements.docker.txt
COPY services/fetch_daily_summaries/src/fetch_daily_summaries ./fetch_daily_summaries

CMD ["fetch_daily_summaries.lambda_handler.lambda_handler"]