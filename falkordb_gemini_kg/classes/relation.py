import json
import re
import logging
from .attribute import Attribute, AttributeType
from falkordb import Node as GraphNode, Edge as GraphEdge
from falkordb_gemini_kg.fixtures.regex import (
    EDGE_LABEL_REGEX,
    NODE_LABEL_REGEX,
    EDGE_REGEX,
)


logger = logging.getLogger(__name__)


class _RelationEntity:
    def __init__(self, label: str):
        self.label = re.sub(r"([^a-zA-Z0-9_])", "", label)

    @staticmethod
    def from_json(txt: str):
        txt = txt if isinstance(txt, dict) else json.loads(txt)
        return _RelationEntity(txt.get("label", txt))

    def to_json(self):
        return {"label": self.label}

    def __str__(self) -> str:
        return f"(:{self.label})"


class Relation:
    def __init__(
        self,
        label: str,
        source: _RelationEntity | str,
        target: _RelationEntity | str,
        attributes: list[Attribute] = None,
    ):
        attributes = attributes or []
        if isinstance(source, str):
            source = _RelationEntity(source)
        if isinstance(target, str):
            target = _RelationEntity(target)

        assert isinstance(label, str), "Label must be a string"
        assert isinstance(source, _RelationEntity), "Source must be an EdgeNode"
        assert isinstance(target, _RelationEntity), "Target must be an EdgeNode"
        assert isinstance(attributes, list), "Attributes must be a list"

        self.label = re.sub(r"([^a-zA-Z0-9_])", "", label.upper())
        self.source = source
        self.target = target
        self.attributes = attributes

    @staticmethod
    def from_graph(relation: GraphEdge, entities: list[GraphNode]):
        logger.debug(f"Relation.from_graph: {relation}")
        return Relation(
            relation.relation,
            _RelationEntity(
                next(n.labels[0] for n in entities if n.id == relation.src_node)
            ),
            _RelationEntity(
                next(n.labels[0] for n in entities if n.id == relation.dest_node)
            ),
            [
                Attribute.from_string(f"{attr}:{relation.properties[attr]}")
                for attr in relation.properties
            ],
        )

    @staticmethod
    def from_json(txt: dict | str):
        txt = txt if isinstance(txt, dict) else json.loads(txt)
        return Relation(
            txt["label"],
            _RelationEntity.from_json(txt["source"]),
            _RelationEntity.from_json(txt["target"]),
            (
                [Attribute.from_json(attr) for attr in txt["attributes"]]
                if "attributes" in txt
                else []
            ),
        )

    @staticmethod
    def from_string(txt: str):
        label = re.search(EDGE_LABEL_REGEX, txt).group(0).strip()
        source = re.search(NODE_LABEL_REGEX, txt).group(0).strip()
        target = re.search(NODE_LABEL_REGEX, txt).group(1).strip()
        relation = re.search(EDGE_REGEX, txt).group(0)
        attributes = (
            relation.split("{")[1].split("}")[0].strip().split(",")
            if "{" in relation
            else []
        )

        return Relation(
            label,
            _RelationEntity(source),
            _RelationEntity(target),
            [Attribute.from_string(attr) for attr in attributes],
        )

    def to_json(self):
        return {
            "label": self.label,
            "source": self.source.to_json(),
            "target": self.target.to_json(),
            "attributes": [attr.to_json() for attr in self.attributes],
        }

    def combine(self, relation2: "Relation"):
        """Overwrite attributes of self with attributes of relation2."""
        if self.label != relation2.label:
            raise Exception("Relations must have the same label to be combined")

        for attr in relation2.attributes:
            if attr.name not in [a.name for a in self.attributes]:
                logger.debug(f"Adding attribute {attr.name} to relation {self.label}")
                self.attributes.append(attr)

        return self

    def to_graph_query(self):
        return f"MATCH (s:{self.source.label}) MATCH (t:{self.target.label}) MERGE (s)-[r:{self.label} {{{', '.join([str(attr) for attr in self.attributes])}}}]->(t) RETURN r"

    def __str__(self) -> str:
        return f"{self.source}-[:{self.label} {{{', '.join([str(attr) for attr in self.attributes])}}}]->{self.target}"
