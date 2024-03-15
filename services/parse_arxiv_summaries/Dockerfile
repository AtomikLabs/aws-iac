FROM public.ecr.aws/lambda/python:3.9
WORKDIR /var/task

COPY services/parse_arxiv_summaries/src/requirements.txt .
COPY services/parse_arxiv_summaries/src/requirements.docker.txt .

RUN python -m pip install -r requirements.docker.txt
COPY services/parse_arxiv_summaries/src/parse_arxiv_summaries ./parse_arxiv_summaries

CMD ["parse_arxiv_summaries.lambda_handler.lambda_handler"]