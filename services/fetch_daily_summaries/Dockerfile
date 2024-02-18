FROM public.ecr.aws/lambda/python:3.9
WORKDIR /var/task
COPY services/fetch_daily_summaries/requirements.txt /app
COPY services/fetch_daily_summaries/requirements.docker.txt /app
RUN python -m pip install -r requirements.docker.txt
COPY services/fetch_daily_summaries/src /app
CMD ["fetch_daily_summaries.lambda_handler"]