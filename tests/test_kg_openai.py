from dotenv import load_dotenv

load_dotenv()
from falkordb_gemini_kg.classes.ontology import Ontology
from falkordb_gemini_kg.classes.node import Node
from falkordb_gemini_kg.classes.edge import Edge
from falkordb_gemini_kg.classes.attribute import Attribute, AttributeType
import unittest
from falkordb_gemini_kg.classes.source import Source
from falkordb_gemini_kg.models.openai import OpenAiGenerativeModel
from falkordb_gemini_kg import KnowledgeGraph, KnowledgeGraphModelConfig
import vertexai
import os
import logging
from falkordb import FalkorDB

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class TestKGOpenAI(unittest.TestCase):
    """
    Test Knowledge Graph
    """

    @classmethod
    def setUpClass(cls):

        cls.ontology = Ontology([], [])

        cls.ontology.add_node(
            Node(
                label="Actor",
                attributes=[
                    Attribute(
                        name="name",
                        attr_type=AttributeType.STRING,
                        unique=True,
                        required=True,
                    ),
                ],
            )
        )
        cls.ontology.add_node(
            Node(
                label="Movie",
                attributes=[
                    Attribute(
                        name="title",
                        attr_type=AttributeType.STRING,
                        unique=True,
                        required=True,
                    ),
                ],
            )
        )
        cls.ontology.add_edge(
            Edge(
                label="ACTED_IN",
                source="Actor",
                target="Movie",
                attributes=[
                    Attribute(
                        name="role",
                        attr_type=AttributeType.STRING,
                        unique=False,
                        required=False,
                    ),
                ],
            )
        )
        cls.graph_name = "IMDB_openai"
        model = OpenAiGenerativeModel(model_name="gpt-3.5-turbo-0125")
        cls.kg = KnowledgeGraph(
            name=cls.graph_name,
            ontology=cls.ontology,
            model_config=KnowledgeGraphModelConfig.with_model(model),
        )

    def test_kg_creation(self):

        file_path = "tests/data/madoff.txt"

        sources = [Source(file_path)]

        self.kg.process_sources(sources)

        answer = self.kg.ask("List a few actors")

        logger.info(f"Answer: {answer}")

        assert "Joseph Scotto" in answer, "Joseph Scotto not found in answer"

    def test_kg_delete(self):

        self.kg.delete()

        db = FalkorDB()
        graphs = db.list_graphs()
        self.assertNotIn(self.graph_name, graphs)
