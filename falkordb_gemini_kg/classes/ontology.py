import json
from falkordb import Graph
from falkordb_gemini_kg.classes.source import AbstractSource
from falkordb_gemini_kg.models import GenerativeModel
import falkordb_gemini_kg
import logging
from .relation import Relation
from .entity import Entity

logger = logging.getLogger(__name__)


class Ontology(object):
    def __init__(self, entities: list[Entity] = None, relations: list[Relation] = None):
        self.entities = entities or []
        self.relations = relations or []

    @staticmethod
    def from_sources(
        sources: list[AbstractSource],
        boundaries: str,
        model: GenerativeModel,
    ) -> "Ontology":
        step = falkordb_gemini_kg.CreateOntologyStep(
            sources=sources,
            ontology=Ontology(),
            model=model,
        )

        return step.run(boundaries=boundaries)

    @staticmethod
    def from_json(txt: dict | str):
        txt = txt if isinstance(txt, dict) else json.loads(txt)
        return Ontology(
            [Entity.from_json(entity) for entity in txt["entities"]],
            [Relation.from_json(relation) for relation in txt["relations"]],
        )

    @staticmethod
    def from_graph(graph: Graph):
        ontology = Ontology()

        entities = graph.query("MATCH (n) RETURN n").result_set
        for entity in entities:
            ontology.add_entity(Entity.from_graph(entity[0]))

        for relation in graph.query("MATCH ()-[r]->() RETURN r").result_set:
            ontology.add_relation(
                Relation.from_graph(relation[0], [x for xs in entities for x in xs])
            )

        return ontology

    def add_entity(self, entity: Entity):
        self.entities.append(entity)

    def add_relation(self, relation: Relation):
        self.relations.append(relation)

    def to_json(self):
        return {
            "entities": [entity.to_json() for entity in self.entities],
            "relations": [relation.to_json() for relation in self.relations],
        }

    def merge_with(self, o: "Ontology"):
        # Merge entities
        for entity in o.entities:
            if entity.label not in [n.label for n in self.entities]:
                # Entity does not exist in self, add it
                self.entities.append(entity)
                logger.debug(f"Adding entity {entity.label}")
            else:
                # Entity exists in self, merge attributes
                entity1 = next(n for n in self.entities if n.label == entity.label)
                entity1.merge(entity)

        # Merge relations
        for relation in o.relations:
            if relation.label not in [e.label for e in self.relations]:
                # Relation does not exist in self, add it
                self.relations.append(relation)
                logger.debug(f"Adding relation {relation.label}")
            else:
                # Relation exists in self, merge attributes
                relation1 = next(e for e in self.relations if e.label == relation.label)
                relation1.combine(relation)

        return self

    def discard_entities_without_relations(self):
        entities_to_discard = [
            entity.label
            for entity in self.entities
            if all(
                [
                    relation.source.label != entity.label
                    and relation.target.label != entity.label
                    for relation in self.relations
                ]
            )
        ]

        self.entities = [
            entity
            for entity in self.entities
            if entity.label not in entities_to_discard
        ]
        self.relations = [
            relation
            for relation in self.relations
            if relation.source.label not in entities_to_discard
            and relation.target.label not in entities_to_discard
        ]

        if len(entities_to_discard) > 0:
            logger.info(f"Discarded entities: {', '.join(entities_to_discard)}")

        return self

    def discard_relations_without_entities(self):
        relations_to_discard = [
            relation.label
            for relation in self.relations
            if relation.source.label not in [entity.label for entity in self.entities]
            or relation.target.label not in [entity.label for entity in self.entities]
        ]

        self.relations = [
            relation
            for relation in self.relations
            if relation.label not in relations_to_discard
        ]

        if len(relations_to_discard) > 0:
            logger.info(f"Discarded relations: {', '.join(relations_to_discard)}")

        return self

    def validate_entities(self):
        # Check for entities without unique attributes
        entities_without_unique_attributes = [
            entity.label
            for entity in self.entities
            if len(entity.get_unique_attributes()) == 0
        ]
        if len(entities_without_unique_attributes) > 0:
            logger.warn(
                f"""
*** WARNING ***
The following entities do not have unique attributes:
{', '.join(entities_without_unique_attributes)}
"""
            )
            return False
        return True

    def get_entity_with_label(self, label: str):
        return next((n for n in self.entities if n.label == label), None)

    def get_relations_with_label(self, label: str):
        return [e for e in self.relations if e.label == label]

    def has_entity_with_label(self, label: str):
        return any(n.label == label for n in self.entities)

    def has_relation_with_label(self, label: str):
        return any(e.label == label for e in self.relations)

    def __str__(self) -> str:
        return "Entities:\n\f- {entities}\n\nEdges:\n\f- {relations}".format(
            entities="\n- ".join([str(entity) for entity in self.entities]),
            relations="\n- ".join([str(relation) for relation in self.relations]),
        )

    def save_to_graph(self, graph: Graph):
        for entity in self.entities:
            query = entity.to_graph_query()
            logger.debug(f"Query: {query}")
            graph.query(query)

        for relation in self.relations:
            query = relation.to_graph_query()
            logger.debug(f"Query: {query}")
            graph.query(query)
