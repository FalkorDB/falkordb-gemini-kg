from falkordb_gemini_kg.kg import KnowledgeGraph
from .agent import Agent
from falkordb_gemini_kg.models import GenerativeModelChatSession


class KGAgent(Agent):
    """Represents an Agent for a FalkorDB Knowledge Graph.

    Args:
        agent_id (str): The ID of the agent.
        kg (KnowledgeGraph): The knowledge graph to query.
        introduction (str): The introduction to the agent.

    Examples:
        >>> from falkordb_gemini_kg import KnowledgeGraph, Orchestrator
        >>> from falkordb_gemini_kg.agents.kg_agent import KGAgent
        >>> orchestrator = Orchestrator(model)
        >>> kg = KnowledgeGraph("test_kg", ontology, model)
        >>> agent = KGAgent("test_agent", kg, "This is a test agent.")
        >>> orchestrator.register_agent(agent)

    """

    _interface = [
        {
            "name": "prompt",
            "type": "string",
            "required": True,
            "description": "The prompt to ask the agent.",
        }
    ]

    def __init__(self, agent_id: str, kg: KnowledgeGraph, introduction: str):
        super().__init__()
        self.agent_id = agent_id
        self.introduction = introduction
        self.kg = kg

    @property
    def agent_id(self) -> str:
        return self._agent_id

    @agent_id.setter
    def agent_id(self, value):
        self._agent_id = value

    @property
    def introduction(self) -> str:
        return self._introduction

    @introduction.setter
    def introduction(self, value):
        self._introduction = value

    @property
    def interface(self) -> list[dict]:
        return self._interface

    @property
    def kg(self) -> KnowledgeGraph:
        return self._kg

    @kg.setter
    def kg(self, value: KnowledgeGraph):
        self._kg = value

    def run(
        self, params: dict, session: GenerativeModelChatSession | None = None
    ) -> tuple[str, GenerativeModelChatSession]:
        """
        Ask the agent a question.

        Args:
            params (dict): The parameters for the agent.

        Returns:
            str: The agent's response.

        """
        (output, chat_session) = self._kg.ask(params["prompt"], session)
        return (output, chat_session)

    def __repr__(self):
        return f"""
---
Agent ID: {self.agent_id}
Knowledge Graph Name: {self._kg.name}
Interface: {self.interface}

Introduction: {self.introduction}
"""
