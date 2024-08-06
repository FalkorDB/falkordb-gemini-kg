from dotenv import load_dotenv

load_dotenv()
from falkordb_gemini_kg.classes.ontology import Ontology
from falkordb_gemini_kg.classes.entity import Entity
from falkordb_gemini_kg.classes.relation import Relation
from falkordb_gemini_kg.classes.attribute import Attribute, AttributeType
import unittest
from falkordb_gemini_kg.classes.source import Source
from falkordb_gemini_kg.models.ollama import OllamaGenerativeModel
from falkordb_gemini_kg import KnowledgeGraph, KnowledgeGraphModelConfig
import os
import logging
from falkordb import FalkorDB

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class TestKGOllama(unittest.TestCase):
    """
    Test Knowledge Graph
    """

    @classmethod
    def setUpClass(cls):

        cls.ontology = Ontology([], [])

        cls.ontology.add_entity(
            Entity(
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
        cls.ontology.add_entity(
            Entity(
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
        cls.ontology.add_relation(
            Relation(
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

        cls.graph_name = "IMDB_ollama"

        model = OllamaGenerativeModel(model_name="gemma2:2b")
        cls.kg = KnowledgeGraph(
            name=cls.graph_name,
            ontology=cls.ontology,
            model_config=KnowledgeGraphModelConfig.with_model(model),
        )

    def test_kg_creation(self):

        raise unittest.SkipTest("not ready for testing")

        file_path = "tests/data/madoff.txt"

        sources = [Source(file_path)]

        self.kg.process_sources(sources)

        answer = self.kg.ask("List a few actors")

        logger.info(f"Answer: {answer}")

        assert "Joseph Scotto" in answer[0], "Joseph Scotto not found in answer"

    def test_kg_delete(self):

        raise unittest.SkipTest("not ready for testing")

        self.kg.delete()

        db = FalkorDB()
        graphs = db.list_graphs()
        self.assertNotIn(self.graph_name, graphs)
