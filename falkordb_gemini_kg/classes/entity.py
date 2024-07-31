import json
import logging
from .attribute import Attribute, AttributeType
from falkordb import Node as GraphNode
import re

logger = logging.getLogger(__name__)

descriptionKey = "__description__"


class Entity:
    def __init__(self, label: str, attributes: list[Attribute], description: str = ""):
        self.label = re.sub(r"([^a-zA-Z0-9_])", "", label)
        self.attributes = attributes
        self.description = description

    @staticmethod
    def from_graph(entity: GraphNode):
        logger.debug(f"Entity.from_graph: {entity}")
        return Entity(
            entity.labels[0],
            [
                Attribute.from_string(f"{attr}:{entity.properties[attr]}")
                for attr in entity.properties
                if attr != descriptionKey
            ],
            entity.properties.get(descriptionKey, ""),
        )

    @staticmethod
    def from_json(txt: dict | str):
        txt = txt if isinstance(txt, dict) else json.loads(txt)
        return Entity(
            txt["label"],
            [Attribute.from_json(attr) for attr in (txt.get("attributes", []))],
            txt.get("description", ""),
        )

    def to_json(self):
        return {
            "label": self.label,
            "attributes": [attr.to_json() for attr in self.attributes],
            "description": self.description,
        }

    def merge(self, entity2: "Entity"):
        """Overwrite attributes of self with attributes of entity2."""
        if self.label != entity2.label:
            raise Exception("Entities must have the same label to be combined")

        for attr in entity2.attributes:
            if attr.name not in [a.name for a in self.attributes]:
                logger.debug(f"Adding attribute {attr.name} to entity {self.label}")
                self.attributes.append(attr)

        return self

    def get_unique_attributes(self):
        return [attr for attr in self.attributes if attr.unique]

    def to_graph_query(self):
        unique_attributes = ", ".join(
            [str(attr) for attr in self.attributes if attr.unique]
        )
        non_unique_attributes = ", ".join(
            [str(attr) for attr in self.attributes if not attr.unique]
        )
        if self.description:
            non_unique_attributes += f"{', ' if len(non_unique_attributes) > 0 else ''} {descriptionKey}: '{self.description}'"
        return f"MERGE (n:{self.label} {{{unique_attributes}}}) SET n += {{{non_unique_attributes}}} RETURN n"

    def __str__(self) -> str:
        return (
            f"(:{self.label} {{{', '.join([str(attr) for attr in self.attributes])}}})"
        )
