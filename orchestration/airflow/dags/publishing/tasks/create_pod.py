import re
from datetime import datetime, timedelta
from html import unescape
from logging.config import dictConfig
from typing import Dict, List, Tuple

import boto3
import structlog
from dotenv import load_dotenv
from neo4j import GraphDatabase
from pytz import timezone
from shared.database.s3_manager import S3Manager
from shared.utils.constants import (
    AIRFLOW_DAGS_ENV_PATH,
    ARXIV_RESEARCH_DATE_FORMAT,
    AWS_REGION,
    CATEGORIZED_BY,
    CATEGORIZES,
    CS_CATEGORIES,
    DATA_BUCKET,
    DEFAULT_TIMEZONE,
    ENVIRONMENT_NAME,
    LOGGING_CONFIG,
    PODS_PREFIX,
    PRIMARILY_CATEGORIZED_BY,
    RECORDS_PREFIX,
    RETRIEVAL_ERRORS,
)
from shared.utils.utils import get_config

dictConfig(LOGGING_CONFIG)

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()
load_dotenv(dotenv_path=AIRFLOW_DAGS_ENV_PATH)

SET_MAP = {"CS": CS_CATEGORIES}


def run(
    arxiv_set: str,
    category: str,
    **context: dict,
):
    try:
        env_vars = [AWS_REGION, DATA_BUCKET, ENVIRONMENT_NAME, PODS_PREFIX, RECORDS_PREFIX]
        config = get_config(context, env_vars, True)
        date_list = next_pod_dates(config, arxiv_set, category)
        for pod_date in date_list:
            try:
                logger.info("Creating pod", set=arxiv_set, category=category, date=pod_date)
                summaries = get_summaries(config, arxiv_set, category, pod_date)
                if not summaries or len(summaries) == 0:
                    logger.info("No summaries for date", set=arxiv_set, category=category, date=pod_date)
                    continue
                pod_summaries = get_pod_summaries(context, config, summaries)
                scripts = write_pod_script(config, pod_summaries, arxiv_set, category, pod_date)
                for key, script in scripts:
                    create_audio(config, arxiv_set, category, pod_date, script, key)
                # logger.info("Pod created", set=arxiv_set, category=category, date=pod_date, file=filename)
            except Exception as e:
                logger.error("Error creating pod", set=arxiv_set, category=category, date=pod_date, error=e)
                continue
        return {"statusCode": 200, "body": "Pod created", "date_list": date_list}
    except Exception as e:
        logger.error("Error creating pod", set=arxiv_set, category=category, error=e)
        return {"statusCode": 500, "body": "Error creating pod"}


def next_pod_dates(config: dict, arxiv_set: str, category: str) -> List[datetime]:
    logger.debug("Getting next pod dates")
    try:
        driver = GraphDatabase.driver(config["NEO4J_URI"], auth=(config["NEO4J_USERNAME"], config["NEO4J_PASSWORD"]))
        with driver.session() as session:
            query = (
                f"MATCH (s:ArxivSet {{code: $arxiv_set}}) "
                f"-[:{CATEGORIZED_BY}]->(c:ArxivCategory {{code: $category}}) "
                f"-[:{CATEGORIZES}]->(p:Podcast) "
                "RETURN p.date ORDER BY p.date DESC LIMIT 1"
            )
            result = session.run(query, {"arxiv_set": arxiv_set, "category": category})
            data = result.data()
            start_date = None
            tzinfo = timezone(DEFAULT_TIMEZONE)
            end_date = datetime.now(tzinfo)
            if len(data) == 0:
                start_date = end_date - timedelta(days=5)
            else:
                start_date = datetime.combine(data[0]["p.date"].to_native(), datetime.min.time(), tzinfo)
            date_list = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]
            return date_list
    except Exception as e:
        logger.error("Error getting last pod date", error=e)
        raise e


def get_summaries(config: dict, arxiv_set: str, category: str, episode_date: datetime) -> List[Dict]:
    logger.debug(
        "Getting summaries", set=arxiv_set, category=category, date=episode_date, method=get_summaries.__name__
    )
    try:
        driver = GraphDatabase.driver(config["NEO4J_URI"], auth=(config["NEO4J_USERNAME"], config["NEO4J_PASSWORD"]))
        with driver.session() as session:
            query = (
                f"MATCH (s:ArxivSet {{code: $arxiv_set}}) "
                f"-[:{CATEGORIZED_BY}]->(c:ArxivCategory {{code: $category}}) "
                f"<-[:{PRIMARILY_CATEGORIZED_BY}]-(a:ArxivRecord)--(b:Abstract) "
                "MATCH (a)-[:AUTHORED_BY]->(author:Author)"
                "WHERE a.date = $date "
                "RETURN {record: a, abstract: b, authors: collect(author)} AS result"
            )
            result = session.run(query, {"arxiv_set": arxiv_set, "category": category, "date": episode_date.date()})
            data = result.data()
            logger.info(
                "Found summaries for target date", set=arxiv_set, category=category, date=episode_date, data=len(data)
            )
            return data
    except Exception as e:
        logger.error("Error getting summaries", error=e, method=get_summaries.__name__)
        raise e


def get_pod_summaries(context: dict, config: dict, summaries: List[Dict]) -> List[Dict]:
    logger.info("Getting pod summaries", num_summaries=len(summaries), method=get_pod_summaries.__name__)
    s3_manager = S3Manager(config[DATA_BUCKET], logger)
    retrieval_errors = []
    for result in summaries:
        try:
            if "result" not in result:
                raise KeyError("Missing 'result' key in summary")
            if "record" not in result["result"]:
                raise KeyError("Missing 'record' key in result")
            record = result["result"]["record"]
            key = f"{config[RECORDS_PREFIX]}/{record['arxiv_id']}/abstract.json"
            raw_data = s3_manager.load(key)
            data = raw_data.decode("utf-8")
            result["result"]["abstract"]["text"] = data.strip()
        except KeyError as e:
            logger.error("KeyError encountered", error=str(e), result=result)
            retrieval_errors.append(result)
            continue
        except Exception as e:
            logger.error("Error getting pod summary", error=str(e), method=get_pod_summaries.__name__)
            retrieval_errors.append(result)
            continue
    logger.info(RETRIEVAL_ERRORS, retrieval_errors=retrieval_errors, method=get_pod_summaries.__name__)
    return summaries


def write_pod_script(
    config: dict, pod_summaries: List[Dict], arxiv_set: str, category: str, episode_date: datetime
) -> List[Tuple[str, str, List[str]]]:
    logger.debug(
        "Writing pod script",
        set=arxiv_set,
        category=category,
        date=episode_date,
        method=write_pod_script.__name__,
    )
    try:
        long_date = get_long_date(episode_date)
        categories_dict = SET_MAP[arxiv_set]
        show_name = categories_dict[category]
        intro_template = (
            f"Hi, and welcome to Tech crafting AI {show_name}. I am your virtual host, Sage. "
            f"Tech crafting AI {show_name} brings you daily summaries of new research released on archive. "
            "The podcast is produced by Brad Edwards. Thank you to archive "
            f"for use of its open access interoperability. "
        )
        outro = "That's all for today, thank you for listening. If you found the podcast helpful, please leave a comment, like, or share it with a friend. See you tomorrow!"

        scripts = []
        num_summaries = len(pod_summaries)
        if num_summaries > 50:
            num_parts = (num_summaries + 29) // 30
            summaries_per_part = (num_summaries + num_parts - 1) // num_parts
        else:
            num_parts = 1
            summaries_per_part = num_summaries

        for part in range(num_parts):
            start_index = part * summaries_per_part
            end_index = min(start_index + summaries_per_part, num_summaries)
            part_summaries = pod_summaries[start_index:end_index]

            if num_parts > 1:
                intro = intro_template + f"Here is Part {part + 1} of what was submitted on {long_date}\n\n"
            else:
                intro = intro_template + f"Here is what was submitted on {long_date}\n\n"
            part_record_ids = []
            script_content = intro
            for research in part_summaries:
                try:
                    r = research["result"]
                    cleaned_title = re.sub(r"\n\s*", " ", r["record"]["title"])
                    script_content += cleaned_title + "\n"

                    authors = [f"{author['first_name']} {author['last_name']}" for author in r["authors"]]
                    script_content += "by " + ", ".join(authors) + "\n\n"

                    paragraphs = r["abstract"]["text"].split("\n\n")
                    for p in paragraphs:
                        cleaned_paragraph = re.sub(r"\n\s*", " ", p)
                        no_latex_paragraph = latex_to_human_readable(cleaned_paragraph)
                        script_content += no_latex_paragraph + "\n\n"
                    part_record_ids.append(r["record"]["arxiv_id"])
                except Exception as e:
                    logger.error("Error writing pod script", error=e, method=write_pod_script.__name__, record=r)
                    continue

            script_content += outro
            part_suffix = f"_part_{part + 1}" if num_parts > 1 else ""
            key = f"{config[PODS_PREFIX]}/{episode_date.strftime(ARXIV_RESEARCH_DATE_FORMAT)}/{arxiv_set}_{category}_script{part_suffix}.txt".lower()
            s3_manager = S3Manager(config[DATA_BUCKET], logger)
            s3_manager.upload_to_s3(key, script_content)
            scripts.append((key, script_content, part_record_ids))

        return scripts
    except Exception as e:
        logger.error("Error getting pod script", error=e, method=write_pod_script.__name__)
        raise e


def get_long_date(episode_date: datetime):
    long_date = episode_date.strftime("%B %d, %Y")
    return long_date


def create_audio(
    config: dict, arxiv_set: str, category: str, episode_date: datetime, script_text: str, key: str
) -> str:
    logger.debug("Generating podcast audio", method=create_audio.__name__)
    part = 0
    match = re.search(r"part_(\d+)", key, re.IGNORECASE)
    if match:
        part = int(match.group(1))
    part_text = f"part_{part}_" if part > 0 else ""
    filename = f"{config[PODS_PREFIX]}/{episode_date.strftime(ARXIV_RESEARCH_DATE_FORMAT)}/{arxiv_set}_{category}_{part_text}podcast".lower()
    try:
        polly_client = boto3.client("polly")
        polly_client.start_speech_synthesis_task(
            OutputFormat="mp3",
            OutputS3BucketName=config[DATA_BUCKET],
            OutputS3KeyPrefix=filename,
            Text=script_text,
            TextType="text",
            VoiceId="Matthew",
        )
        return filename
    except Exception as e:
        logger.error(f"Failed to create Polly audio for {filename}")
        logger.error(e)
    return None


def latex_to_human_readable(latex_str):
    # Remove $...$ delimiters
    latex_str = re.sub(r"\$(.*?)\$", r"\1", latex_str)

    simple_latex_to_text = {
        "\\ll": "<<",
        "\\alpha": "alpha",
        "\\epsilon": "epsilon",
        "\\widetilde": "widetilde",
        "\\in": "in",
        "\\leq": "<=",
        "\\geq": ">=",
        "\\pm": "±",
        "\\times": "x",
        "\\sim": "~",
        "\\approx": "≈",
        "\\neq": "≠",
        "\\cdot": "·",
        "\\ldots": "...",
        "\\cdots": "...",
        "\\vdots": "...",
        "\\ddots": "...",
        "\\forall": "for all",
        "\\exists": "exists",
        "\\nabla": "nabla",
        "\\partial": "partial",
        "\\{": "{",
        "\\}": "}",
        "\\:": " ",  # Small space
        "\\,": " ",  # Thin space
        "\\;": " ",  # Thick space
        "\\!": "",  # Negative space
        "_": "_",  # Subscript
    }

    for latex, text in simple_latex_to_text.items():
        latex_str = latex_str.replace(latex, text)

    single_arg_pattern = re.compile(r"\\(\w+){(.*?)}")
    latex_str = single_arg_pattern.sub(r"\2", latex_str)

    latex_str = latex_str.replace("``", '"').replace("''", '"')

    latex_str = latex_str.replace("--", "–")

    return unescape(latex_str)
