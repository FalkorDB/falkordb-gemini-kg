from falkordb_gemini_kg.steps.Step import Step
from falkordb_gemini_kg.classes.source import AbstractSource
from concurrent.futures import Future, ThreadPoolExecutor, wait
from falkordb_gemini_kg.classes.ontology import Ontology
from falkordb_gemini_kg.classes.model_config import StepModelConfig
from vertexai.generative_models import (
    GenerativeModel,
    ChatSession,
    ResponseValidationError,
    GenerationResponse,
    FinishReason,
)
from falkordb_gemini_kg.fixtures.prompts import (
    EXTRACT_DATA_SYSTEM,
    EXTRACT_DATA_PROMPT,
    FIX_JSON_PROMPT,
)
import logging
from falkordb_gemini_kg.helpers import extract_json, map_dict_to_cypher_properties
import json
from falkordb import Graph
from falkordb_gemini_kg.classes.Document import Document
from uuid import uuid4
import os
import time
from ratelimit import limits, sleep_and_retry

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class ExtractDataStep(Step):
    """
    Extract Data Step
    """

    def __init__(
        self,
        sources: list[AbstractSource],
        ontology: Ontology,
        model_config: StepModelConfig,
        graph: Graph,
        config: dict = {
            "max_workers": 16,
            "max_input_tokens": 500000,
            "max_output_tokens": 8192,
        },
    ) -> None:
        self.sources = sources
        self.ontology = ontology
        self.config = config
        self.model_config = model_config
        self.graph = graph

        if not os.path.exists("logs"):
            os.makedirs("logs")

    def _create_chat(self):
        return GenerativeModel(
            self.model_config.model,
            generation_config=(
                self.model_config.generation_config.to_generation_config()
                if self.model_config.generation_config is not None
                else None
            ),
            system_instruction=EXTRACT_DATA_SYSTEM.replace(
                "#ONTOLOGY", str(self.ontology.to_json())
            ),
        ).start_chat(response_validation=False)

    def run(self):

        tasks: list[Future[Ontology]] = []
        with ThreadPoolExecutor(max_workers=self.config["max_workers"]) as executor:
            # extract entities and relationships from each page
            documents = [
                document
                for source in self.sources
                for document in source.load()
                if document is not None
                and document.content is not None
                and len(document.content) > 0
            ]
            logger.debug(f"Processing {len(documents)} documents")
            for document in documents:
                task_id = "extract_data_step_" + str(uuid4())
                task = executor.submit(
                    self._process_source,
                    task_id,
                    self._create_chat(),
                    document,
                    self.ontology,
                    self.graph,
                )
                tasks.append(task)

            # Wait for all tasks to complete
            wait(tasks)

    def _process_source(
        self,
        task_id: str,
        chat_session: ChatSession,
        document: Document,
        ontology: Ontology,
        graph: Graph,
    ):
        try:
            _task_logger = logging.getLogger(task_id)
            _task_logger.setLevel(logging.DEBUG)

            fh = logging.FileHandler(f"logs/{task_id}.log")
            fh.setFormatter(
                logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                )
            )
            fh.setLevel(logging.DEBUG)

            _task_logger.addHandler(fh)

            logger.debug(f"Processing task: {task_id}")
            _task_logger.debug(f"Processing task: {task_id}")
            text = document.content[: self.config["max_input_tokens"]]
            user_message = EXTRACT_DATA_PROMPT.format(text=text)

            # logger.debug(f"User message: {user_message}")
            _task_logger.debug("User message: " + user_message.replace("\n", " "))

            responses: list[GenerationResponse] = []
            response_idx = 0

            responses.append(self._call_model(chat_session, user_message))

            _task_logger.debug(f"Model response: {responses[response_idx]}")

            while (
                responses[response_idx].candidates[0].finish_reason
                == FinishReason.MAX_TOKENS
            ):
                _task_logger.debug("Asking model to continue")
                response_idx += 1
                responses.append(self._call_model(chat_session, "continue"))
                _task_logger.debug(
                    f"Model response after continue: {responses[response_idx].text}"
                )

            if responses[response_idx].candidates[0].finish_reason != FinishReason.STOP:
                _task_logger.debug(
                    f"Model stopped unexpectedly: {responses[response_idx].candidates[0].finish_reason}"
                )
                raise Exception(
                    f"Model stopped unexpectedly: {responses[response_idx].candidates[0].finish_reason}"
                )

            combined_text = " ".join([r.text for r in responses])

            try:
                data = json.loads(extract_json(combined_text))
            except json.decoder.JSONDecodeError as e:
                _task_logger.debug(f"Error extracting JSON: {e}")
                _task_logger.debug(f"Prompting model to fix JSON")
                json_fix_response = self._call_model(
                    self._create_chat(),
                    FIX_JSON_PROMPT.format(json=combined_text, error=str(e)),
                )
                data = json.loads(extract_json(json_fix_response.text))
                _task_logger.debug(f"Fixed JSON: {data}")

            if not "nodes" in data or not "edges" in data:
                _task_logger.debug(f"Invalid data format: {data}")
                raise Exception(f"Invalid data format: {data}")

            for node in data["nodes"]:
                try:
                    self._create_node(graph, node, ontology)
                except Exception as e:
                    logger.exception(e)
                    continue

            for edge in data["edges"]:
                try:
                    self._create_edge(graph, edge, ontology)
                except Exception as e:
                    logger.exception(e)
                    continue
        except Exception as e:
            logger.exception(e)
            raise e

    def _create_node(self, graph: Graph, args: dict, ontology: Ontology):
        # Get unique attributes from node
        node = ontology.get_node_with_label(args["label"])
        if node is None:
            print(f"Node with label {args['label']} not found in ontology")
            return None
        unique_attributes_schema = [attr for attr in node.attributes if attr.unique]
        unique_attributes = {
            attr.name: (
                args["attributes"][attr.name] if attr.name in args["attributes"] else ""
            )
            for attr in unique_attributes_schema
        }
        unique_attributes_text = map_dict_to_cypher_properties(unique_attributes)
        non_unique_attributes = {
            attr.name: args["attributes"][attr.name]
            for attr in node.attributes
            if not attr.unique and attr.name in args["attributes"]
        }
        non_unique_attributes_text = map_dict_to_cypher_properties(
            non_unique_attributes
        )
        set_statement = (
            f"SET n += {non_unique_attributes_text}"
            if len(non_unique_attributes.keys()) > 0
            else ""
        )
        query = f"MERGE (n:{args['label']} {unique_attributes_text}) {set_statement}"
        logger.debug(f"Query: {query}")
        result = graph.query(query)
        return result

    def _create_edge(self, graph: Graph, args: dict, ontology: Ontology):
        edge = ontology.get_edge_with_label(args["label"])
        if edge is None:
            print(f"Edge with label {args['label']} not found in ontology")
            return None
        source_unique_attributes = (
            args["source"]["attributes"]
            if "source" in args and "attributes" in args["source"]
            else {}
        )
        source_unique_attributes_text = map_dict_to_cypher_properties(
            source_unique_attributes
        )

        target_unique_attributes = (
            args["target"]["attributes"]
            if "target" in args and "attributes" in args["target"]
            else {}
        )
        target_unique_attributes_text = map_dict_to_cypher_properties(
            target_unique_attributes
        )

        edge_attributes = (
            map_dict_to_cypher_properties(args["attributes"])
            if "attributes" in args
            else {}
        )
        set_statement = (
            f"SET r += {edge_attributes}"
            if "attributes" in args
            and len(
                args["attributes"]
                if isinstance(args["attributes"], list)
                else args["attributes"].keys()
            )
            > 0
            else ""
        )
        query = f"MATCH (s:{args['source']['label']} {source_unique_attributes_text}) MATCH (d:{args['target']['label']} {target_unique_attributes_text}) MERGE (s)-[r:{args['label']}]->(d) {set_statement}"
        logger.debug(f"Query: {query}")
        result = graph.query(query)
        return result

    @sleep_and_retry
    @limits(calls=15, period=60)
    def _call_model(
        self,
        chat_session: ChatSession,
        prompt: str,
        retry=6,
    ):
        try:
            return chat_session.send_message(prompt)
        except Exception as e:
            # If exception is caused by quota exceeded, wait 10 seconds and try again for 6 times
            if "Quota exceeded" in str(e) and retry > 0:
                time.sleep(10)
                retry -= 1
                return self._call_model(chat_session, prompt, retry)
            else:
                if retry == 0:
                    logger.error("Quota exceeded")
                raise e
