import uuid
from datetime import date

import structlog
from neo4j import GraphDatabase

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

NEO4J                       = "neo4j"
NEO4J_PASSWORD              = "NEO4J_PASSWORD"
NEO4J_URI                   = "NEO4J_URI"
NEO4J_USERNAME              = "NEO4J_USERNAME"

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
                    database_=NEO4J,
                )
                if len(records) == 1:
                    logger.info("arXiv DataSource node found.", method=self.check_arxiv_node_exists.__name__)
                    return records[0].data()
                if len(records) > 1:
                    message = "Multiple arXiv DataSource nodes found. This should not be possible and should be investigated."
                    logger.error(message, method=self.check_arxiv_node_exists.__name__, uri=self.uri, username=self.username)
                    raise ValueError(message)
                logger.info("arXiv DataSource node not found.", method=self.check_arxiv_node_exists.__name__)
                return {}
            except Exception as e:
                logger.error("Error while checking if arXiv DataSource node exists.", method=self.check_arxiv_node_exists.__name__, uri=self.uri, username=self.username, error=str(e))
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
            logger.error(message, method=self.create_arxiv_datasource_node.__name__, uri=self.uri, username=self.username)
            raise ValueError(message)
        with GraphDatabase.driver(self.uri,
                                auth=(self.username, self.password)) as driver:
            try:
                driver.verify_connectivity()
                data = self.check_arxiv_node_exists()
                arxiv_uuid = data.get("uuid")
                if arxiv_uuid:
                    message = "An arXiv DataSource node already exists. Must not create another."
                    logger.error(message, method=self.create_arxiv_datasource_node.__name__, uri=self.uri, username=self.username)
                    return data

                logger.info("arXiv DataSource node not found. Creating it.", method=self.create_arxiv_datasource_node.__name__)
                node_uuid = uuid.uuid4().__str__()
                name = "arXiv"
                url = arxiv_base_url
                description = "arXiv is a free distribution service and an open-access archive for scholarly articles in the fields of physics, mathematics, computer science, quantitative biology, quantitative finance, statistics, electrical engineering and systems science, and economics."

                records, summary, _ = driver.execute_query("""
                    CREATE (d:DataSource {uuid: $uuid, name: $name, url: $url, description: $description}) RETURN d.uuid AS uuid, d.name AS name, d.url AS url, d.description AS description
                    """, uuid=node_uuid, name=name, url=url, description=description, database_=NEO4J,
                )

                if summary.counters.nodes_created != 1:
                    message = "Failed to create arXiv DataSource node or multiple nodes were created."
                    logger.error(message, method=self.create_arxiv_datasource_node.__name__, uri=self.uri, username=self.username, records_created=summary.counters.nodes_created)
                    raise RuntimeError(message)
                logger.info("Created arXiv nodes in {time} ms.".format(
                    time=summary.result_available_after
                ), method=self.create_arxiv_datasource_node.__name__)

                return records[0].data()
            except Exception as e:
                logger.error("Failed to create arXiv DataSource node.", method=self.create_arxiv_datasource_node.__name__, uri=self.uri, username=self.username, error=str(e))
                raise e

    def create_arxiv_raw_data_node(self,
                                   date_from: date,
                                   date_to: date,
                                   date_obtained: date,
                                   method_name: str,
                                   method_version: str,
                                   size: int, 
                                   storage_uri: str) -> dict:
        """
        Creates a data node in the Neo4j database.

        Args:
            date_from (date): The earliest date of the data.
            date_to (date): The latest date of the data.
            date_obtained (date): The date the data was obtained.
            method_name (str): The name of the method used to obtain the data.
            method_version (str): The version of the method used to obtain the data.
            size (int): The size of the data.
            storage_uri (str): The URI where the data is stored.
        Raises:
            ValueError: If config, raw_data_key, today, or earliest are not provided.
        """
        if not self.uri or not self.username or not self.password:
            message = "URI, username, and password are required but one or more are not set."
            logger.error(message, method=self.create_arxiv_raw_data_node.__name__, uri=self.uri, username=self.username)
            raise ValueError(message)
        if not date_from or not date_to or not date_obtained or not isinstance(date_from, date) or not isinstance(date_to, date) or not isinstance(date_obtained, date):
            message = "Date from, date to, and date obtained are required and must be dates."
            logger.error(message, method=self.create_arxiv_raw_data_node.__name__, date_from=date_from, date_to=date_to, date_obtained=date_obtained)
            raise ValueError(message)
        if not method_name or not method_version or not isinstance(method_name, str) or not isinstance(method_version, str):
            message = "Method name and method version are required and must be strings."
            logger.error(message, method=self.create_arxiv_raw_data_node.__name__, method_name=method_name, method_version=method_version)
            raise ValueError(message)
        if not size or not storage_uri or not isinstance(size, int) or not isinstance(storage_uri, str):
            message = "Size and storage URI are required and must be integers and strings, respectively."
            logger.error(message, method=self.create_arxiv_raw_data_node.__name__, size=size, storage_uri=storage_uri)
            raise ValueError(message)
        
        with GraphDatabase.driver(self.uri, auth=(self.username, self.password)) as driver:
            try:
                driver.verify_connectivity()
                arxiv = self.check_arxiv_node_exists()
                if not arxiv or not arxiv.get("uuid"):
                    message = "arXiv DataSource node does not exist. Must create it first."
                    logger.error(message, method=self.create_arxiv_raw_data_node.__name__, uri=self.uri, username=self.username, data=arxiv)
                    raise ValueError(message)
                
                data_uuid               = uuid.uuid4().__str__()
                data_desc               = "raw arXiv daily summaries for one or more days and sets."
                data_format             = "xml"
                data_op_uuid            = uuid.uuid4().__str__()
                data_op_name            = "Data Ingestion"
                
                records, summary, _ = driver.execute_query("""
                    MATCH (s:DataSource {uuid: $data_source_uuid})
                    MERGE (d:Data {uuid: $data_uuid, date_from: $date_from, date_to: $date_to, description: $description,  format: $format, storage_uri: $storage_uri, size_bytes: $size_bytes})
                    MERGE (dop:DataOperation {uuid: $dop_uuid, date: $dop_date, method_name: $method_name, method_version: $method_version, name: $dop_name})
                    MERGE (s)-[:CREATES]->(d)
                    MERGE (d)-[:CREATED_BY]->(s)
                    MERGE (d)-[:INGESTED_BY]->(dop)
                    MERGE (dop)-[:INGESTS]->(d)
                    MERGE (dop)-[:OBTAINS_FROM]->(s)
                    MERGE (s)-[:PROVIDES]->(dop)
                    RETURN d, dop, s
                    """,
                    data_source_uuid=arxiv['uuid'],
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
                    database_=NEO4J,
                )
                if summary.counters.nodes_created != 2 and summary.counters.nodes_created != 3 or summary.counters.relationships_created != 6:
                    message = "Failed to create arXiv raw data node or multiple nodes were created."
                    logger.error(message, method=self.create_arxiv_raw_data_node.__name__, uri=self.uri, username=self.username, records_created=summary.counters.nodes_created)
                    raise RuntimeError(message)
                logger.info("Created arXiv raw data nodes in {time} ms.".format(
                    time=summary.result_available_after
                ), method=self.create_arxiv_raw_data_node.__name__)

                return records
            
            except Exception as e:
                    logger.error("Failed to create arXiv raw data node.", method=self.create_arxiv_datasource_node.__name__, uri=self.uri, username=self.username, error=str(e))
                    raise e
        