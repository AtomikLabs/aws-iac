import json
import re
import time
from collections import defaultdict
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
from shared.models.arxiv_category import ArxivCategory
from shared.models.arxiv_record import ArxivRecord
from shared.models.podcast import Podcast
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
    PUBLISHED_IN,
    PUBLISHES,
    RECORDS_PREFIX,
    RETRIEVAL_ERRORS,
    SUMMARIZES,
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
        titles_by_date = defaultdict(list)
        task_ids = []
        notes_data = []
        for pod_date in date_list:
            try:
                logger.info("Creating pod", set=arxiv_set, category=category, date=pod_date)
                summaries = get_summaries(config, arxiv_set, category, pod_date)
                titles_by_date[pod_date] = [s["result"]["record"]["title"] for s in summaries]
                if not summaries or len(summaries) == 0:
                    logger.info("No summaries for date", set=arxiv_set, category=category, date=pod_date)
                    continue
                pod_summaries = get_pod_summaries(context, config, summaries)
                scripts = write_pod_script(
                    config=config,
                    pod_summaries=pod_summaries,
                    arxiv_set=arxiv_set,
                    category=category,
                    episode_date=pod_date,
                )
                part = 0 if len(scripts) == 1 else 1
                for key, script, part_record_ids, titles in scripts:
                    audio_key, audio_task_id = create_audio(
                        config=config,
                        arxiv_set=arxiv_set,
                        category=category,
                        episode_date=pod_date,
                        script_text=script,
                        key=key,
                    )
                    task_ids.append(audio_task_id)
                    marks_uri, marks_task_id = create_speech_marks(
                        config=config,
                        arxiv_set=arxiv_set,
                        category=category,
                        episode_date=pod_date,
                        script_text=script,
                        key=key,
                    )
                    task_ids.append(marks_task_id)
                    notes_data.append((pod_date, category, part, marks_uri, titles))
                    part += 1
                    create_pod_node(
                        config=config,
                        arxiv_set=arxiv_set,
                        category=category,
                        pod_date=pod_date,
                        script_key=key,
                        audio_key=audio_key,
                        part_record_ids=part_record_ids,
                    )
            except Exception as e:
                logger.error("Error creating pod", set=arxiv_set, category=category, date=pod_date, error=e)
                continue
        pods_created_time = poll_polly_jobs(config, task_ids)
        if pods_created_time > 10 * 60:
            logger.warn(
                "Pod creation took longer than 10 minutes", duration=pods_created_time, method="create_pod_task"
            )
        for pod_date, category, part, marks_key, titles in notes_data:
            create_pod_notes(config, pod_date, category, part, marks_key, titles)
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
                "RETURN p.episode_date ORDER BY p.episode_date DESC LIMIT 1"
            )
            result = session.run(query, {"arxiv_set": arxiv_set, "category": category})
            data = result.data()
            start_date = None
            tzinfo = timezone(DEFAULT_TIMEZONE)
            end_date = datetime.now(tzinfo) + timedelta(days=1)
            if len(data) == 0:
                start_date = end_date - timedelta(days=5)
            else:
                start_date = datetime.combine(
                    data[0]["p.episode_date"].to_native(), datetime.min.time(), tzinfo
                ) + timedelta(days=1)
            date_list = []
            current_date = start_date
            while current_date < end_date:
                date_list.append(current_date)
                current_date += timedelta(days=1)
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
                f"<-[:{PRIMARILY_CATEGORIZED_BY}]-(a:ArxivRecord)<-[:{SUMMARIZES}]-(b:Abstract) "
                "MATCH (a)-[:AUTHORED_BY]->(author:Author)"
                "WHERE a.date = $date "
                "RETURN {record: a, abstract: b, authors: collect({first_name: author.first_name, last_name: author.last_name})} AS result"
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
) -> List[Tuple[str, str, List[str], List[str]]]:
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
            f"<speak>Hi, and welcome to Tech crafting AI {show_name}. I am your virtual host, Sage. "
            f"Tech crafting AI {show_name} brings you daily summaries of new research released on archive. "
            "The podcast is produced by Brad Edwards. Thank you to archive "
            f"for use of its open access interoperability. "
        )
        outro = "That's all for today, thank you for listening. If you found the podcast helpful, please leave a comment, like, or share it with a friend. See you tomorrow!</speak>"

        scripts = []
        num_summaries = len(pod_summaries)
        if num_summaries > 50:
            num_parts = (num_summaries + 39) // 40
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
            timepoint = 0
            titles = []
            for research in part_summaries:
                try:
                    r = research["result"]
                    cleaned_title = re.sub(r"\n\s*", " ", escape_special_chars(r["record"]["title"]))
                    titles.append(cleaned_title)
                    script_content += f'<mark name="{timepoint}"/>' + cleaned_title + "\n"
                    timepoint += 1
                    authors = [
                        escape_special_chars(f"{author['first_name']} {author['last_name']}") for author in r["authors"]
                    ]
                    script_content += "by " + ", ".join(authors) + "\n\n"

                    paragraphs = r["abstract"]["text"].split("\n\n")
                    for p in paragraphs:
                        cleaned_paragraph = re.sub(r"\n\s*", " ", p)
                        no_latex_paragraph = latex_to_human_readable(cleaned_paragraph)
                        escaped_paragraph = escape_special_chars(no_latex_paragraph)
                        script_content += escaped_paragraph + "\n\n"
                    part_record_ids.append(r["record"]["arxiv_id"])
                except Exception as e:
                    logger.error("Error writing pod script", error=e, method=write_pod_script.__name__)
                    continue

            script_content += outro
            part_suffix = f"_part_{part + 1}" if num_parts > 1 else ""
            key = f"{config[PODS_PREFIX]}/{episode_date.strftime(ARXIV_RESEARCH_DATE_FORMAT)}/{arxiv_set}_{category}_script{part_suffix}.txt".lower()
            s3_manager = S3Manager(config[DATA_BUCKET], logger)
            s3_manager.upload_to_s3(key, script_content)
            scripts.append((key, script_content, part_record_ids, titles))
        return scripts
    except Exception as e:
        logger.error("Error getting pod script", error=e, method=write_pod_script.__name__)
        raise e


def escape_special_chars(text: str) -> str:
    """Escape special characters for SSML."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("'", "&apos;")
        .replace('"', "&quot;")
    )


def unescape_special_chars(text: str) -> str:
    """Unescape special characters for SSML."""
    return (
        text.replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&apos;", "'")
        .replace("&quot;", '"')
    )


def get_long_date(episode_date: datetime):
    long_date = episode_date.strftime("%B %d, %Y")
    return long_date


def create_audio(
    config: dict, arxiv_set: str, category: str, episode_date: datetime, script_text: str, key: str
) -> Tuple[str, str]:
    logger.debug("Generating podcast audio", method=create_audio.__name__)
    part = 0
    match = re.search(r"part_(\d+)", key, re.IGNORECASE)
    if match:
        part = int(match.group(1))
    part_text = f"part_{part}_" if part > 0 else ""
    filename = f"{config[PODS_PREFIX]}/{episode_date.strftime(ARXIV_RESEARCH_DATE_FORMAT)}/{arxiv_set}_{category}_{part_text}podcast".lower()
    try:
        polly_client = boto3.client("polly")
        response = polly_client.start_speech_synthesis_task(
            Engine="standard",
            LanguageCode="en-US",
            OutputFormat="mp3",
            OutputS3BucketName=config[DATA_BUCKET],
            OutputS3KeyPrefix=filename,
            Text=script_text,
            TextType="ssml",
            VoiceId="Matthew",
        )
        task_id = response["SynthesisTask"]["TaskId"]
        return filename, task_id
    except Exception as e:
        logger.error(f"Failed to create Polly audio for {filename}")
        logger.error(e)
        return None


def create_speech_marks(
    config: dict, arxiv_set: str, category: str, episode_date: datetime, script_text: str, key: str
) -> Tuple[str, str]:
    logger.debug("Generating speech marks", method=create_speech_marks.__name__)
    part = 0
    match = re.search(r"part_(\d+)", key, re.IGNORECASE)
    if match:
        part = int(match.group(1))
    part_text = f"part_{part}_" if part > 0 else ""
    filename = f"{config[PODS_PREFIX]}/{episode_date.strftime(ARXIV_RESEARCH_DATE_FORMAT)}/{arxiv_set}_{category}_{part_text}speech_marks".lower()
    try:
        polly_client = boto3.client("polly")
        response = polly_client.start_speech_synthesis_task(
            Engine="standard",
            LanguageCode="en-US",
            OutputFormat="json",
            OutputS3BucketName=config[DATA_BUCKET],
            OutputS3KeyPrefix=filename,
            SpeechMarkTypes=["ssml"],
            Text=script_text,
            TextType="ssml",
            VoiceId="Matthew",
        )
        task_id = response["SynthesisTask"]["TaskId"]
        output_uri = response["SynthesisTask"]["OutputUri"]
        return output_uri, task_id
    except Exception as e:
        logger.error(f"Failed to create Polly speech marks for {filename}")
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


def create_pod_node(
    config: dict,
    arxiv_set: str,
    category: str,
    pod_date: datetime,
    script_key: str,
    audio_key: str,
    part_record_ids: List[str],
):
    logger.debug("Creating pod node", method=create_pod_node.__name__)
    episode = 1
    season = 1
    part = 0
    match = re.search(r"part_(\d+)", script_key, re.IGNORECASE)
    if match:
        part = int(match.group(1))
    part_text = f"Part {part} - " if part > 0 else ""
    title = f"Episode {episode} - {part_text}{get_long_date(pod_date)}"
    try:
        with GraphDatabase.driver(
            config["NEO4J_URI"], auth=(config["NEO4J_USERNAME"], config["NEO4J_PASSWORD"])
        ) as driver:
            query = (
                f"MATCH (s:ArxivSet {{code: $arxiv_set}}) "
                f"-[:{CATEGORIZED_BY}]->(c:ArxivCategory {{code: $category}}) "
                f"-[:{CATEGORIZES}]->(p:Podcast) "
                "RETURN {episode: p.episode, season: p.season} AS result ORDER BY p.episode_date DESC LIMIT 1"
            )
            with driver.session() as session:
                result = session.run(query, {"arxiv_set": arxiv_set, "category": category})
                data = result.data()
                if len(data) > 0:
                    episode = data[0]["result"]["episode"] + 1
                    season = data[0]["result"]["season"]

            pod = Podcast(
                driver=driver,
                title=title,
                season=season,
                episode=episode,
                part=part,
                episode_date=pod_date.date(),
                script_key=script_key,
                audio_key=audio_key,
            )
            pod.create()

            category_node = ArxivCategory.find(driver, category)
            if not category_node:
                logger.error("Category node not found", category=category, pod=pod, method=create_pod_node.__name__)
                raise ValueError(f"Category node not found: {category}")
            pod.relate(
                driver=driver,
                label=CATEGORIZED_BY,
                start_label=Podcast.LABEL,
                start_uuid=pod.uuid,
                end_label=ArxivCategory.LABEL,
                end_uuid=category_node.uuid,
            )
            category_node.relate(
                driver=driver,
                label=CATEGORIZES,
                start_label=ArxivCategory.LABEL,
                start_uuid=category_node.uuid,
                end_label=Podcast.LABEL,
                end_uuid=pod.uuid,
            )

            for record_id in part_record_ids:
                try:
                    record_node = ArxivRecord.find(driver, record_id)
                    if not record_node:
                        logger.error(
                            "Record node not found", record_id=record_id, pod=pod, method=create_pod_node.__name__
                        )
                        continue
                    pod.relate(
                        driver=driver,
                        label=PUBLISHES,
                        start_label=Podcast.LABEL,
                        start_uuid=pod.uuid,
                        end_label=ArxivRecord.LABEL,
                        end_uuid=record_node.uuid,
                    )
                    record_node.relate(
                        driver=driver,
                        label=PUBLISHED_IN,
                        start_label=ArxivRecord.LABEL,
                        start_uuid=record_node.uuid,
                        end_label=Podcast.LABEL,
                        end_uuid=pod.uuid,
                    )
                except Exception as e:
                    logger.error(
                        "Error creating pod node", error=e, record_id=record_id, method=create_pod_node.__name__
                    )
                    continue
    except Exception as e:
        logger.error("Error creating pod node", error=e, method=create_pod_node.__name__)
        raise e


def poll_polly_jobs(config: dict, task_ids: List[str], timeout_minutes: int = 15) -> float:
    polly_client = boto3.client("polly")
    timeout_seconds = timeout_minutes * 60
    poll_interval = 15
    start_time = time.time()

    while time.time() - start_time < timeout_seconds:
        all_done = True
        for task_id in task_ids:
            response = polly_client.get_speech_synthesis_task(TaskId=task_id)
            status = response["SynthesisTask"]["TaskStatus"]
            if status not in ["completed", "failed"]:
                all_done = False
                break

        if all_done:
            duration = time.time() - start_time
            logger.info("Polly jobs completed", duration=duration, method=poll_polly_jobs.__name__)
            return duration

        time.sleep(poll_interval)

    raise TimeoutError("Polling Polly jobs timed out after 15 minutes.")


def create_pod_notes(
    config: dict, episode_date: datetime, category: str, part_number: int, marks_key_prefix: str, titles: List[str]
):
    logger.debug("Creating pod notes", method=create_pod_notes.__name__)
    s3_manager = S3Manager(config[DATA_BUCKET], logger)

    if marks_key_prefix.startswith("https://"):
        marks_key_prefix = marks_key_prefix.split(f"{config['DATA_BUCKET']}/")[-1]

    timeout_seconds = 300
    poll_interval = 10
    start_time = time.time()
    marks_key = None
    logger.info("mkp", mkp=marks_key_prefix)
    while time.time() - start_time < timeout_seconds:
        try:
            contents = s3_manager.list(marks_key_prefix)
            if contents and len(contents) > 0:
                logger.info("contents", contents=contents)
                for obj in contents:
                    if obj["Key"].startswith(marks_key_prefix) and obj["Key"].endswith(".marks"):
                        marks_key = obj["Key"]
                        break
            if marks_key:
                break
        except Exception as e:
            logger.error("Error accessing S3 during polling", error=str(e))
        time.sleep(poll_interval)

    if not marks_key:
        logger.error("Failed to find marks file with prefix", prefix=marks_key_prefix)
        raise FileNotFoundError(f"No marks file found with prefix {marks_key_prefix}")

    try:
        logger.info("marks key", mk=marks_key)
        obj = s3_manager.load(marks_key)
        marks_data = obj["Body"].read().decode("utf-8")
        marks = [json.loads(line) for line in marks_data.splitlines()]
    except Exception as e:
        logger.error("Failed to retrieve marks file", key=marks_key, error=str(e))
        raise

    episode_notes = []
    episode_notes.append(f"ArXiv {CS_CATEGORIES[category]} research for {episode_date.strftime('%A, %B %d, %Y')}.\n")
    for i, mark in enumerate(marks):
        if i >= len(titles):
            break
        time_ms = mark["time"]
        minutes, seconds = divmod(time_ms // 1000, 60)
        timestamp = f"{minutes:02}:{seconds:02}"
        episode_note = f"{timestamp}: {unescape_special_chars(titles[i])}"
        episode_notes.append(episode_note)

    part_chunk = "" if part_number == 0 else f"_part_{part_number}"
    notes_key = f"{config['PODS_PREFIX']}/{episode_date.strftime('%Y-%m-%d')}/{category}{part_chunk}_episode_notes.txt"
    try:
        s3_manager.upload_to_s3(key=notes_key, content="\n".join(episode_notes))
        logger.info("Pod notes created and uploaded", date=episode_date, s3_key=notes_key)
    except Exception as e:
        logger.error("Failed to upload pod notes", key=notes_key, error=str(e))
        raise
