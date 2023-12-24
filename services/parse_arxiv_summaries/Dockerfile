FROM public.ecr.aws/lambda/python:3.9
WORKDIR ${LAMBDA_TASK_ROOT}
COPY services/parse_arxiv_summaries/requirements.txt .
RUN python -m pip install -r requirements.txt
COPY services/parse_arxiv_summaries/src .
CMD ["parse_arxiv_summaries.lambda_handler"]