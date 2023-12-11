FROM public.ecr.aws/lambda/python:3.9
WORKDIR ${LAMBDA_TASK_ROOT}
COPY services/fetch_daily_summaries/requirements.txt .
RUN python -m pip install -r requirements.txt
COPY services/fetch_daily_summaries/src .
CMD ["fetch_daily_summaries.lambda_handler"]