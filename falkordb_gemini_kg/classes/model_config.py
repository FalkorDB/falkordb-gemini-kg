from falkordb_gemini_kg.models import GenerativeModel


class KnowledgeGraphModelConfig:

    def __init__(
        self,
        extract_data: GenerativeModel,
        cypher_generation: GenerativeModel,
        qa: GenerativeModel,
    ):
        self.extract_data = extract_data
        self.cypher_generation = cypher_generation
        self.qa = qa

    @staticmethod
    def with_model(model: GenerativeModel):
        return KnowledgeGraphModelConfig(
            extract_data=model,
            cypher_generation=model,
            qa=model,
        )
    
    @staticmethod
    def from_json(json: dict) -> "KnowledgeGraphModelConfig":
        return KnowledgeGraphModelConfig(
            GenerativeModel.from_json(json["extract_data"]),
            GenerativeModel.from_json(json["cypher_generation"]),
            GenerativeModel.from_json(json["qa"]),
        )
    
    def to_json(self) -> dict:
        return {
            "extract_data": self.extract_data.to_json(),
            "cypher_generation": self.cypher_generation.to_json(),
            "qa": self.qa.to_json(),
        }
