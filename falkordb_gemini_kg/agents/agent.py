from abc import ABC, abstractmethod
from falkordb_gemini_kg.models.model import GenerativeModelChatSession


class AgentResponseCode:
    AGENT_RESPONSE = "agent_response"
    AGENT_ERROR = "agent_error"
    AGENT_REQUEST_INPUT = "agent_request_input"

    @staticmethod
    def from_str(text: str) -> "AgentResponseCode":
        if text == AgentResponseCode.AGENT_RESPONSE:
            return AgentResponseCode.AGENT_RESPONSE
        elif text == AgentResponseCode.AGENT_ERROR:
            return AgentResponseCode.AGENT_ERROR
        elif text == AgentResponseCode.AGENT_REQUEST_INPUT:
            return AgentResponseCode.AGENT_REQUEST_INPUT
        else:
            raise ValueError(f"Unknown agent response code: {text}")


class AgentResponse:

    def __init__(self, response_code: AgentResponseCode, payload: dict):
        self.response_code = response_code
        self.payload = payload

    def to_json(self) -> dict:
        return {
            "response_code": self.response_code,
            "payload": self.payload,
        }

    @staticmethod
    def from_json(json: dict) -> "AgentResponse":
        return AgentResponse(
            AgentResponseCode.from_str(json["response_code"]),
            json["payload"],
        )

    def __str__(self) -> str:
        return (
            f"AgentResponse(response_code={self.response_code}, payload={self.payload})"
        )

    def __repr__(self) -> str:
        return str(self)


class Agent(ABC):

    @property
    @abstractmethod
    def agent_id(self) -> str:
        pass

    @property
    @abstractmethod
    def introduction(self) -> str:
        pass

    @property
    @abstractmethod
    def interface(self) -> list[dict]:
        pass

    @abstractmethod
    def run(
        self, params: dict, session: GenerativeModelChatSession
    ) -> tuple[str, GenerativeModelChatSession]:
        pass

    @abstractmethod
    def __repr__(self) -> str:
        pass
