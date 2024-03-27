import uuid
from datetime import date, datetime

import structlog
from constants import DEFAULT_NEO4J_DB
from neo4j import GraphDatabase
from storage_manager import StorageManager

structlog.configure(
    [
        structlog.stdlib.filter_by_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.dict_tracebacks,
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger()

# TODO: Generalize defensive programming checks


class Neo4jDatabase:
    """
    A class to interact with the AtomikLabs Neo4j database.
    """

    def __init__(self, uri: str, username: str, password: str) -> None:
        """
        Initializes the GraphDatabase class.

        Args:
            uri (str): The URI of the Neo4j database.
            username (str): The username of the Neo4j database.
            password (str): The password of the Neo4j database.

        Raises:
            ValueError: If password, uri, or user are not provided.
        """
        if not password or not uri or not username:
            message = "Password, URI, and user are required."
            logger.error(message, method=Neo4jDatabase.__init__.__name__, uri=uri, username=username)
            raise ValueError(message)
        if not isinstance(password, str) or not isinstance(uri, str) or not isinstance(username, str):
            message = "Password, URI, and user must be strings."
            logger.error(message, method=Neo4jDatabase.__init__.__name__, uri=uri, username=username)
            raise ValueError(message)

        self.password = password
        self.uri = uri
        self.username = username

    def create_arxiv_raw_data_node(
        self,
        date_from: date,
        date_to: date,
        date_obtained: datetime,
        method_name: str,
        method_version: str,
        size: int,
        bucket_name: str,
        storage_uri: str,
    ) -> dict:
        """
        Creates a data node in the Neo4j database.

        Args:
            date_from (date): The earliest date of the data.
            date_to (date): The latest date of the data.
            date_obtained (date): The date the data was obtained.
            method_name (str): The name of the method used to obtain the data.
            method_version (str): The version of the method used to obtain the data.
            size (int): The size of the data.
            bucket_name (str): The name of the bucket where the data is stored.
            storage_uri (str): The URI where the data is stored.
        Raises:
            ValueError: If config, raw_data_key, today, or earliest are not provided.
        """
        if not self.uri or not self.username or not self.password:
            message = "URI, username, and password are required but one or more are not set."
            logger.error(message, method=self.create_arxiv_raw_data_node.__name__, uri=self.uri, username=self.username)
            raise ValueError(message)
        if (
            not date_from
            or not date_to
            or not date_obtained
            or not method_name
            or not method_version
            or not size
            or not bucket_name
            or not storage_uri
        ):
            message = "Date from, date to, date obtained, method name, method version, size, bucket name, and storage URI are required."
            logger.error(
                message,
                method=self.create_arxiv_raw_data_node.__name__,
                date_from=date_from,
                date_to=date_to,
                date_obtained=date_obtained,
                dop_method_name=method_name,
                dop_method_version=method_version,
                size=size,
                bucket_name=bucket_name,
                storage_uri=storage_uri,
            )
            raise ValueError(message)
        if not isinstance(date_from, date) or not isinstance(date_to, date) or not isinstance(date_obtained, datetime):
            message = "Date from, date to, and date obtained must be dates."
            logger.error(
                message,
                method=self.create_arxiv_raw_data_node.__name__,
                date_from=date_from,
                date_to=date_to,
                date_obtained=date_obtained,
            )
            raise ValueError(message)
        if (
            not isinstance(method_name, str)
            or not isinstance(method_version, str)
            or not isinstance(bucket_name, str)
            or not isinstance(storage_uri, str)
        ):
            message = "Method name, method version, bucket name, and storage URI must be strings."
            logger.error(
                message,
                method=self.create_arxiv_raw_data_node.__name__,
                dop_method_name=method_name,
                dop_method_version=method_version,
                bucket_name=bucket_name,
                storage_uri=storage_uri,
            )
            raise ValueError(message)
        if not isinstance(size, int):
            message = "Size must be an integer."
            logger.error(
                message,
                method=self.create_arxiv_raw_data_node.__name__,
                size=size,
            )
            raise ValueError(message)

        with GraphDatabase.driver(self.uri, auth=(self.username, self.password)) as driver:
            try:
                driver.verify_connectivity()
                arxiv = self.check_arxiv_node_exists()
                if not arxiv or not arxiv.get("uuid"):
                    message = "arXiv DataSource node does not exist. Must create it first."
                    logger.error(
                        message,
                        method=self.create_arxiv_raw_data_node.__name__,
                        uri=self.uri,
                        username=self.username,
                        data=arxiv,
                    )
                    raise ValueError(message)

                data_uuid = uuid.uuid4().__str__()
                data_desc = "raw arXiv daily summaries for one or more days and sets."
                data_format = "xml"
                data_op_uuid = uuid.uuid4().__str__()
                data_op_name = "Data Ingestion"
                ingested_by_uuid = uuid.uuid4().__str__()
                ingests_uuid = uuid.uuid4().__str__()
                obtains_from_uuid = uuid.uuid4().__str__()
                provides_uuid = uuid.uuid4().__str__()

                records, summary, _ = driver.execute_query(
                    """
                    MATCH (s:DataSource {uuid: $data_source_uuid})
                    MERGE (d:Data {uuid: $data_uuid, date_from: $date_from, date_to: $date_to, description: $description,  format: $format, storage_uri: $storage_uri, size_bytes: $size_bytes})
                    MERGE (dop:DataOperation {uuid: $dop_uuid, date: $dop_date, method_name: $method_name, method_version: $method_version, name: $dop_name})
                    MERGE (d)-[:INGESTED_BY {uuid: $ingested_by_uuid}]->(dop)
                    MERGE (dop)-[:INGESTS {uuid: $ingests_uuid}]->(d)
                    MERGE (dop)-[:OBTAINS_FROM {uuid: $obtains_from_uuid}]->(s)
                    MERGE (s)-[:PROVIDES {uuid: $provides_uuid}]->(dop)
                    RETURN d, dop, s
                    """,
                    data_source_uuid=arxiv["uuid"],
                    data_uuid=data_uuid,
                    date_from=date_from,
                    date_to=date_to,
                    description=data_desc,
                    format=data_format,
                    storage_uri=storage_uri,
                    size_bytes=size,
                    dop_uuid=data_op_uuid,
                    dop_date=date_obtained,
                    method_name=method_name,
                    method_version=method_version,
                    dop_name=data_op_name,
                    ingested_by_uuid=ingested_by_uuid,
                    ingests_uuid=ingests_uuid,
                    obtains_from_uuid=obtains_from_uuid,
                    provides_uuid=provides_uuid,
                    database_=DEFAULT_NEO4J_DB,
                )
                if (
                    summary.counters.nodes_created != 2 and summary.counters.nodes_created != 3
                ) or summary.counters.relationships_created != 4:
                    message = "Failed to create arXiv raw data node or multiple nodes were created."
                    logger.error(
                        message,
                        method=self.create_arxiv_raw_data_node.__name__,
                        uri=self.uri,
                        username=self.username,
                        records_created=summary.counters.nodes_created,
                    )
                    raise RuntimeError(message)
                logger.info(
                    "Created arXiv raw data nodes in {time} ms.".format(time=summary.result_available_after),
                    method=self.create_arxiv_raw_data_node.__name__,
                )

                return records

            except Exception as e:
                logger.error(
                    "Failed to create arXiv raw data node.",
                    method=self.create_arxiv_datasource_node.__name__,
                    uri=self.uri,
                    username=self.username,
                    error=str(e),
                )
                raise e

    def check_arxiv_node_exists(self) -> dict:
        """
        Checks if the arXiv node exists.

        Returns:
            dict: The arXiv node or and empty dict if it does not exist.

        Raises:
            RuntimeError: If the database connection fails.
            ValueError: if URI, username, or password are not set.
            ValueError: if multiple arXiv nodes are found. This should never happen and should be investigated.
        """
        if not self.uri or not self.username or not self.password:
            message = "URI, username, and password are required but one or more are not set."
            logger.error(message, method=self.check_arxiv_node_exists.__name__, uri=self.uri, username=self.username)
            raise ValueError(message)

        with GraphDatabase.driver(self.uri, auth=(self.username, self.password)) as driver:
            try:
                driver.verify_connectivity()
                records, _, _ = driver.execute_query(
                    "MATCH (d:DataSource {name: 'arXiv'}) RETURN d.uuid AS uuid, d.name AS name, d.url AS url, d.description AS description",
                    database_=DEFAULT_NEO4J_DB,
                )
                if len(records) == 1:
                    logger.info("arXiv DataSource node found.", method=self.check_arxiv_node_exists.__name__)
                    return records[0].data()
                if len(records) > 1:
                    message = (
                        "Multiple arXiv DataSource nodes found. This should not be possible and should be investigated."
                    )
                    logger.error(
                        message, method=self.check_arxiv_node_exists.__name__, uri=self.uri, username=self.username
                    )
                    raise ValueError(message)
                logger.info("arXiv DataSource node not found.", method=self.check_arxiv_node_exists.__name__)
                return {}
            except Exception as e:
                logger.error(
                    "Error while checking if arXiv DataSource node exists.",
                    method=self.check_arxiv_node_exists.__name__,
                    uri=self.uri,
                    username=self.username,
                    error=str(e),
                )
                raise e

    def create_arxiv_datasource_node(self, arxiv_base_url: str) -> dict:
        """
        Creates the arXiv DataSource node in the Neo4j database.

        Args:
            arxiv_base_url (str): The arXiv base URL for making queries.

        Returns:
            str: The UUID of the arXiv DataSource node.

        Raises:
            RuntimeError: If the database connection fails.
            RuntimeError: If the node is not created.
        """
        if not arxiv_base_url or not isinstance(arxiv_base_url, str):
            message = "arXiv base URL is required and must be a string."
            logger.error(message, method=self.create_arxiv_datasource_node.__name__, arxiv_base_url=arxiv_base_url)
            raise ValueError(message)
        if not self.uri or not self.username or not self.password:
            message = "URI, username, and password are required but one or more are not set."
            logger.error(
                message, method=self.create_arxiv_datasource_node.__name__, uri=self.uri, username=self.username
            )
            raise ValueError(message)
        with GraphDatabase.driver(self.uri, auth=(self.username, self.password)) as driver:
            try:
                driver.verify_connectivity()
                data = self.check_arxiv_node_exists()
                arxiv_uuid = data.get("uuid")
                if arxiv_uuid:
                    message = "An arXiv DataSource node already exists. Must not create another."
                    logger.warn(
                        message, method=self.create_arxiv_datasource_node.__name__, uri=self.uri, username=self.username
                    )
                    return data

                logger.info(
                    "arXiv DataSource node not found. Creating it.", method=self.create_arxiv_datasource_node.__name__
                )
                node_uuid = uuid.uuid4().__str__()
                name = "arXiv"
                url = arxiv_base_url
                description = "arXiv is a free distribution service and an open-access archive for scholarly articles in the fields of physics, mathematics, computer science, quantitative biology, quantitative finance, statistics, electrical engineering and systems science, and economics."

                records, summary, _ = driver.execute_query(
                    """
                    CREATE (d:DataSource {uuid: $uuid, name: $name, url: $url, description: $description}) RETURN d.uuid AS uuid, d.name AS name, d.url AS url, d.description AS description
                    """,
                    uuid=node_uuid,
                    name=name,
                    url=url,
                    description=description,
                    database_=DEFAULT_NEO4J_DB,
                )

                if summary.counters.nodes_created != 1:
                    message = "Failed to create arXiv DataSource node or multiple nodes were created."
                    logger.error(
                        message,
                        method=self.create_arxiv_datasource_node.__name__,
                        uri=self.uri,
                        username=self.username,
                        records_created=summary.counters.nodes_created,
                    )
                    raise RuntimeError(message)
                logger.info(
                    "Created arXiv nodes in {time} ms.".format(time=summary.result_available_after),
                    method=self.create_arxiv_datasource_node.__name__,
                )

                return records[0].data()
            except Exception as e:
                logger.error(
                    "Failed to create arXiv DataSource node.",
                    method=self.create_arxiv_datasource_node.__name__,
                    uri=self.uri,
                    username=self.username,
                    error=str(e),
                )
                raise e

    def check_arxiv_research_exists(self, arXiv_identifier: str) -> dict:
        """
        Checks if an arXiv research record exists in the database. A record is considered duplicate if the
        arXiv identifier matches another record as these are invariant across arXiv submission updates for the
        same paper.

        Args:
            date_created (str): The date the record was created.
            first_parse_uuid (str): The UUID of the first parse operation that created the record.

        Returns:
            dict: The record data if it exists, otherwise an empty dict.

        Raises:
            ValueError: If arXiv_identifier is not provided or is not a string.
            RuntimeError: If the database connection fails.
            RuntimeError: If multiple records are found with the same arXiv identifier.
        """
        if not arXiv_identifier or not isinstance(arXiv_identifier, str):
            message = "arXiv identifier is required and must be a string."
            logger.error(
                message,
                method=self.check_arxiv_record_exists.__name__,
                arXiv_identifier=arXiv_identifier,
            )
            raise ValueError(message)
        try:
            with GraphDatabase.driver(self.uri, auth=(self.username, self.password)) as driver:
                driver.verify_connectivity()
                records, _, _ = driver.execute_query(
                    "MATCH (n:ArxivRecord {arxivId: $arxivId}) RETURN n",
                    arxivId=arXiv_identifier,
                    database_=DEFAULT_NEO4J_DB,
                )
                if len(records) == 1:
                    logger.debug(
                        "Found arXiv record.",
                        method=self.check_arxiv_record_exists.__name__,
                        arXiv_identifier=arXiv_identifier,
                    )
                    return records[0].data()
                if len(records) > 1:
                    message = "Multiple arXiv records found with the same title and date. Investigate."
                    logger.error(
                        message,
                        method=self.check_arxiv_record_exists.__name__,
                        arXiv_identifier=arXiv_identifier,
                    )
                    raise RuntimeError(message)
                return {}
        except Exception as e:
            message = "An error occurred while trying to check if an arXiv record exists."
            logger.error(
                message,
                method=self.check_arxiv_record_exists.__name__,
                error=str(e),
            )
            raise e

    def create_arxiv_parsed_node(
        self,
        raw_data_key: str,
        size_bytes: int,
        service_name: str,
        service_version: str,
        parsed_date: datetime,
        raw_data_bucket_name: str,
        output_key: str,
    ) -> dict:
        """
        Creates a parsed node in the Neo4j database.

        Args:
            raw_data_key (str): The key where the raw data is stored.
            service_name (str): The name of the service that parsed the data.
            service_version (str): The version of the service that parsed the data.
            parsed_date (datetime): The date the data was parsed.
            raw_data_bucket_name (str): The name of the bucket where the raw data is stored.
            output_key (str): The key where the parsed data is stored.

        Returns:
            dict: The parsed node data.

        Raises:
            ValueError: If output_key, service_name, service_version, parsed_date, raw_data_bucket_name, or raw_data_key are not provided.
            RuntimeError: If the database connection fails.
            RuntimeError: If the node is not created.
        """
        if not self.uri or not self.username or not self.password:
            message = "URI, username, and password are required but one or more are not set."
            logger.error(message, method=self.create_arxiv_raw_data_node.__name__, uri=self.uri, username=self.username)
            raise ValueError(message)
        if (
            not output_key
            or not size_bytes
            or not service_name
            or not service_version
            or not parsed_date
            or not raw_data_bucket_name
            or not raw_data_key
        ):
            message = "Output key, size_bytes, service name, service version, parsed date, raw data bucket name, and raw data key are required."
            logger.error(
                message,
                method=self.create_arxiv_parsed_node.__name__,
                output_key=output_key,
                service_name=service_name,
                service_version=service_version,
                parsed_date=parsed_date,
                raw_data_bucket_name=raw_data_bucket_name,
                raw_data_key=raw_data_key,
            )
            raise ValueError(message)
        if (
            not isinstance(output_key, str)
            or not isinstance(service_name, str)
            or not isinstance(service_version, str)
            or not isinstance(raw_data_bucket_name, str)
            or not isinstance(raw_data_key, str)
        ):
            message = (
                "Output key, service name, service version, raw data bucket name, and raw data key must be strings."
            )
            logger.error(
                message,
                method=self.create_arxiv_parsed_node.__name__,
                output_key=output_key,
                service_name=service_name,
                service_version=service_version,
                raw_data_bucket_name=raw_data_bucket_name,
                raw_data_key=raw_data_key,
            )
            raise ValueError(message)
        if not isinstance(size_bytes, int):
            message = "Size bytes must be an integer."
            logger.error(
                message,
                method=self.create_arxiv_parsed_node.__name__,
                size_bytes=size_bytes,
            )
            raise ValueError(message)
        if not isinstance(parsed_date, datetime):
            message = "Parsed date must be a datetime."
            logger.error(
                message,
                method=self.create_arxiv_parsed_node.__name__,
                parsed_date=parsed_date,
            )
            raise ValueError(message)

        with GraphDatabase.driver(self.uri, auth=(self.username, self.password)) as driver:
            try:
                driver.verify_connectivity()

                parsed_uuid = uuid.uuid4().__str__()
                parsed_desc = "Parsed arXiv research summaries."
                parsed_format = "json"
                parsed_bucket = raw_data_bucket_name

                dop_uuid = uuid.uuid4().__str__()
                dop_date = parsed_date
                dop_name = "Parse raw arXiv XML to json."

                parsed_by_uuid = uuid.uuid4().__str__()
                parses_uuid = uuid.uuid4().__str__()
                created_by_uuid = uuid.uuid4().__str__()
                creates_uuid = uuid.uuid4().__str__()

                records, summary, _ = driver.execute_query(
                    """
                    MATCH (d:Data {storage_uri: $raw_data_key})
                    MERGE (p:Data {uuid: $parsed_uuid, description: $parsed_desc, format: $format, bucket: $parsed_bucket, storage_uri: $output_key, size_bytes: $size_bytes})
                    MERGE (dop:DataOperation {uuid: $dop_uuid, date: $dop_date, name: $dop_name, method_name: $service_name, method_version: $service_version})
                    MERGE (d)-[:PARSED_BY {uuid: $parsed_by_uuid}]->(dop)
                    MERGE (dop)-[:PARSES {uuid: $parses_uuid}]->(d)
                    MERGE (p)-[:CREATED_BY {uuid: $created_by_uuid}]->(dop)
                    MERGE (dop)-[:CREATES {uuid: $creates_uuid}]->(p)
                    RETURN p, dop
                    """,
                    raw_data_key=raw_data_key,
                    parsed_uuid=parsed_uuid,
                    parsed_desc=parsed_desc,
                    format=parsed_format,
                    parsed_bucket=parsed_bucket,
                    output_key=output_key,
                    size_bytes=size_bytes,
                    dop_uuid=dop_uuid,
                    dop_date=dop_date,
                    dop_name=dop_name,
                    service_name=service_name,
                    service_version=service_version,
                    parsed_by_uuid=parsed_by_uuid,
                    parses_uuid=parses_uuid,
                    created_by_uuid=created_by_uuid,
                    creates_uuid=creates_uuid,
                    database_=DEFAULT_NEO4J_DB,
                )

                if summary.counters.nodes_created != 2:
                    message = "Failed to create arXiv parsed node or multiple nodes were created."
                    logger.error(
                        message,
                        method=self.create_arxiv_parsed_node.__name__,
                        records_created=summary.counters.nodes_created,
                    )
                    raise RuntimeError(message)
                logger.info(
                    "Created arXiv parsed nodes in {time} ms.".format(time=summary.result_available_after),
                    method=self.create_arxiv_parsed_node.__name__,
                )

                return records

            except Exception as e:
                logger.error(
                    "Failed to create arXiv parsed node.",
                    method=self.create_arxiv_parsed_node.__name__,
                    uri=self.uri,
                    username=self.username,
                    error=str(e),
                )
                raise e

    def store_arxiv_records(self, parse_key: str, records: list, service_name: str, service_version: str) -> dict:
        """
        Stores arxiv research summary records in the neo4j database.

        Args:
            key (str): The key where the parsed data is stored.
            records (list): The arXiv records to store.
            service_name (str): The name of the service that loaded the data.
            service_version (str): The version of the service that loaded the data.

        Returns:
            dict: with the UUIDs of stored records and any that could not be stored.

        Raises:
        """
        if (
            not parse_key
            or not isinstance(parse_key, str)
            or not service_name
            or not isinstance(service_name, str)
            or not service_version
            or not isinstance(service_version, str)
        ):
            message = "Parse key, service name, and service version are required and must be strings."
            logger.error(
                message,
                method=self.store_arxiv_records.__name__,
                parse_key=parse_key,
                service_name=service_name,
                service_version=service_version,
            )
            raise ValueError(message)
        if not records or not isinstance(records, list):
            message = "Records must be present and be a list of dict."
            logger.error(
                message,
                method=self.store_arxiv_records.__name__,
                records_type=type(records),
                records=records,
            )
            raise ValueError(message)

        results = {"stored": [], "failed": []}
        if len(records) == 0:
            return results
        logger.info(
            "Storing parsed arXiv records to neo4j.", method=self.store_arxiv_records.__name__, num_records=len(records)
        )

        with GraphDatabase.driver(self.uri, auth=(self.username, self.password)) as driver:
            try:
                with GraphDatabase.driver(self.uri, auth=(self.username, self.password)) as driver:
                    driver.verify_connectivity()
                    parsed_records, summary, _ = driver.execute_query(
                        """
                        MATCH (d:Data {storage_uri: $parse_key}) RETURN d.uuid AS uuid
                        """,
                        parse_key=parse_key,
                        database_=DEFAULT_NEO4J_DB,
                    )
                    if len(parsed_records) != 1:
                        message = "Data node not found for parse key. Must create it first."
                        logger.error(
                            message,
                            method=self.store_arxiv_records.__name__,
                            parse_key=parse_key,
                            records=parsed_records,
                        )
                        raise ValueError(message)
                    parsed_data_uuid = parsed_records[0].data().get("uuid")
                    now = StorageManager.get_storage_key_datetime()
                    dop_uuid = uuid.uuid4().__str__()
                    dop_name = "Load arXiv records."
                    loaded_by_uuid = uuid.uuid4().__str__()
                    loads_from_uuid = uuid.uuid4().__str__()

                    loaded_by_uuid = uuid.uuid4().__str__()
                    loads_from_uuid = uuid.uuid4().__str__()

                    r, _, _ = driver.execute_query(
                        """
                        MATCH (d:Data {uuid: $parsed_data_uuid})
                        MERGE (dop:DataOperation {uuid: $dop_uuid, date: $now, name: $dop_name, method_name: $service_name, method_version: $service_version, created: $now, last_modified: $now})
                        MERGE (d)-[:LOADED_BY {uuid: $loaded_by_uuid}]->(dop)
                        MERGE (dop)-[:LOADS_FROM {uuid: $loads_from_uuid}]->(d)
                        return dop.uuid AS uuid
                        """,
                        parsed_data_uuid=parsed_data_uuid,
                        dop_uuid=dop_uuid,
                        dop_name=dop_name,
                        service_name=service_name,
                        service_version=service_version,
                        now=now,
                        loaded_by_uuid=loaded_by_uuid,
                        loads_from_uuid=loads_from_uuid,
                        database_=DEFAULT_NEO4J_DB,
                    )
                    if len(r) != 1:
                        message = "Failed to create data operation node."
                        logger.error(
                            message,
                            method=self.store_arxiv_records.__name__,
                            records=r,
                        )
                        raise RuntimeError(message)
                    load_uuid = r[0].data().get("uuid")
                for record in records[:1]:
                    try:
                        arxiv_identifier = record.get("identifier")
                        if not arxiv_identifier:
                            raise ValueError("ArXiv identifier is required.")
                        node = self.create_arxiv_node(record, parsed_data_uuid, load_uuid)
                        results.get("stored").append(node.get("title"))
                    except Exception as e:
                        message = "An error occurred while trying to store an arXiv record."
                        logger.error(
                            message,
                            method=self.store_arxiv_records.__name__,
                            error=str(e),
                            record=record,
                        )
                        results.get("failed").append(record.get("title"))

                logger.info(
                    "Stored arXiv records in neo4j.",
                    method=self.store_arxiv_records.__name__,
                    num_stored=len(results.get("stored")),
                    num_failed=len(results.get("failed")),
                )
            except Exception as e:
                message = "An error occurred while trying to store arXiv records."
                logger.error(
                    message,
                    method=self.store_arxiv_records.__name__,
                    error=str(e),
                )
                raise e
        return results

    def create_arxiv_node(self, record: dict, parsed_data_node: str, load_uuid: str) -> dict:
        if not record or not isinstance(record, dict):
            message = "Record is required and must be a dict."
            logger.error(
                message,
                method=self.create_arxiv_node.__name__,
                record=record,
            )
            raise ValueError(message)
        if (
            not parsed_data_node
            or not isinstance(parsed_data_node, str)
            or not load_uuid
            or not isinstance(load_uuid, str)
        ):
            message = "Parsed data node and load UUID are required and must be strings."
            logger.error(
                message,
                method=self.create_arxiv_node.__name__,
                parsed_data_node=parsed_data_node,
                load_uuid=load_uuid,
            )
            raise ValueError(message)
        try:
            with GraphDatabase.driver(self.uri, auth=(self.username, self.password)) as driver:
                driver.verify_connectivity()

                current_date = StorageManager.get_storage_key_date()

                research_uuid = uuid.uuid4().__str__()
                arxiv_identifier = record.get("identifier")
                research_date = record.get("date")
                title = record.get("title")

                abstract_uuid = uuid.uuid4().__str__()
                abstract = record.get("abstract")
                abstract_url = record.get("abstract_url")

                full_text_uuid = uuid.uuid4().__str__()
                full_text_url = record.get("abstract_url").replace("/abs/", "/pdf/")

                # authors = record.get("authors")

                categories = record.get("categories", [])
                categories_query = "\n".join(
                    [
                        f"MERGE (ar)-[:ArxivCategory {{uuid: '{uuid.uuid4().__str__()}'}}]->(:ArxivCategory {{code: '{cat}'}})"
                        for cat in categories
                    ]
                )
                primary_category = record.get("primary_category", "")

                group = record.get("group", "")

                creates_uuid = uuid.uuid4().__str__()
                created_by_uuid = uuid.uuid4().__str__()
                has_abstract_uuid = uuid.uuid4().__str__()
                abstract_of_uuid = uuid.uuid4().__str__()
                has_full_text_uuid = uuid.uuid4().__str__()
                full_text_of_uuid = uuid.uuid4().__str__()
                belongs_to_uuid = uuid.uuid4().__str__()
                has_research_uuid = uuid.uuid4().__str__()

                records, summary, _ = driver.execute_query(
                    f"""
                    MATCH (d:DataOperation {{uuid: $load_uuid}})
                    MATCH (ac:ArxivCategory {{code: $primary_category}})
                    MATCH (as:ArxivSet {{code: $group}})
                    MERGE (ar:ArxivRecord {{uuid: $research_uuid, arxivId: $arxiv_identifier, date: $research_date, title: $title, created: $current_date, last_modified: $last_modified}})
                    MERGE (ab:Abstract {{uuid: $abstract_uuid, text: $abstract, url: $abstract_url, created: $current_date, last_modified: $current_date}})
                    MERGE (f:FullText {{uuid: $full_text_uuid, url: $full_text_url, created: $current_date, last_modified: $current_date}})
                    MERGE (ar)-[:CREATED_BY {{uuid: $created_by_uuid}}]->(d)
                    MERGE (d)-[:CREATES {{uuid: $creates_uuid}}]->(ar)
                    MERGE (ar)-[:HAS_ABSTRACT {{uuid: $has_abstract_uuid}}]->(ab)
                    MERGE (ar)-[:HAS_FULL_TEXT {{uuid: $has_full_text_uuid}}]->(f)
                    MERGE (ab)-[:ABSTRACT_OF {{uuid: $abstract_of_uuid}}]->(ar)
                    MERGE (f)-[:FULL_TEXT_OF {{uuid: $full_text_of_uuid}}]->(ar)
                    MERGE (ar)-[:BELONGS_TO {{uuid: $belongs_to_uuid}}]->(ac)
                    MERGE (ac)-[:HAS_RESEARCH {{uuid: $research_uuid}}]->(ar)
                    {categories_query}
                    RETURN ar
                    """,
                    load_uuid=load_uuid,
                    primary_category=primary_category,
                    group=group,
                    research_uuid=research_uuid,
                    arxiv_identifier=arxiv_identifier,
                    research_date=research_date,
                    title=title,
                    current_date=current_date,
                    last_modified=current_date,
                    abstract_uuid=abstract_uuid,
                    abstract=abstract,
                    abstract_url=abstract_url,
                    full_text_uuid=full_text_uuid,
                    full_text_url=full_text_url,
                    created_by_uuid=created_by_uuid,
                    creates_uuid=creates_uuid,
                    has_abstract_uuid=has_abstract_uuid,
                    abstract_of_uuid=abstract_of_uuid,
                    has_full_text_uuid=has_full_text_uuid,
                    full_text_of_uuid=full_text_of_uuid,
                    belongs_to_uuid=belongs_to_uuid,
                    has_research_uuid=has_research_uuid,
                    database_=DEFAULT_NEO4J_DB,
                )

                if summary.counters.nodes_created != 1:
                    message = "Failed to create arXiv record node or multiple nodes were created."
                    logger.error(
                        message,
                        method=self.create_arxiv_node.__name__,
                        records_created=summary.counters.nodes_created,
                    )
                    raise RuntimeError(message)
                logger.debug(
                    "Created arXiv record node in {time} ms.".format(time=summary.result_available_after),
                    method=self.create_arxiv_node.__name__,
                    uuid=research_uuid,
                )
                return records[0].data()
        except Exception as e:
            message = "An error occurred while trying to create an arXiv record."
            logger.error(
                message,
                method=self.create_arxiv_node.__name__,
                error=str(e),
            )
            raise e

    def create_researcher_node(self, author: str) -> dict:
        raise NotImplementedError

    def create_research_node(self, record: dict, parsed_data_node: str) -> dict:
        raise NotImplementedError

    def create_abstract_node(self, record: dict, parsed_data_node: str) -> dict:
        raise NotImplementedError

    def create_full_text_node(self, record: dict, parsed_data_node: str) -> dict:
        raise NotImplementedError

    def create_arxiv_set_node(self, record: dict, parsed_data_node: str) -> dict:
        raise NotImplementedError

    def get_node_by_uuid(self, node_uuid: str) -> dict:
        """
        Get a node by its UUID.

        Args:
            none_uuid (str): The UUID of the node to get.

        Returns:
            dict: The node data.
        """
        if not node_uuid or not isinstance(uuid, str):
            message = "UUID is required and must be a string."
            logger.error(
                message,
                method=self.get_node_by_uuid.__name__,
                uuid=node_uuid,
            )
            raise ValueError(message)
        with GraphDatabase.driver(self.uri, auth=(self.username, self.password)) as driver:
            try:
                driver.verify_connectivity()
                records, _, _ = driver.execute_query(
                    "MATCH (n) WHERE n.uuid = $uuid RETURN n",
                    uuid=node_uuid,
                    database_=DEFAULT_NEO4J_DB,
                )
                if len(records) == 1:
                    logger.debug("Found node by UUID.", method=self.get_node_by_uuid.__name__, uuid=node_uuid)
                    return records[0].data()
                if len(records) > 1:
                    message = "Multiple nodes found with the same UUID. Investigate."
                    logger.error(
                        message,
                        method=self.get_node_by_uuid.__name__,
                        uuid=node_uuid,
                    )
                    raise ValueError(message)
                return {}
            except Exception as e:
                message = "An error occurred while trying to get a node by UUID."
                logger.error(
                    message,
                    method=self.get_node_by_uuid.__name__,
                    error=str(e),
                )
                raise e
