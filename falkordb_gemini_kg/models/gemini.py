from .model import *
from vertexai.generative_models import (
    GenerativeModel as VertexAiGenerativeModel,
    GenerationConfig as VertexAiGenerationConfig,
    GenerationResponse as VertexAiGenerationResponse,
    FinishReason as VertexAiFinishReason,
)


class GeminiGenerativeModel(GenerativeModel):

    _model: VertexAiGenerativeModel = None

    def __init__(
        self,
        model_name: str,
        generation_config: GenerativeModelConfig | None = None,
        system_instruction: str | None = None,
    ):
        self._model_name = model_name
        self._generation_config = generation_config
        self._system_instruction = system_instruction

    def _get_model(self) -> VertexAiGenerativeModel:
        if self._model is None:
            self._model = VertexAiGenerativeModel(
                self._model_name,
                generation_config=(
                    VertexAiGenerationConfig(
                        temperature=self._generation_config.temperature,
                        top_p=self._generation_config.top_p,
                        top_k=self._generation_config.top_k,
                        max_output_tokens=self._generation_config.max_output_tokens,
                        stop_sequences=self._generation_config.stop_sequences,
                    )
                    if self._generation_config is not None
                    else None
                ),
                system_instruction=self._system_instruction,
            )

        return self._model

    def with_system_instruction(self, system_instruction: str) -> "GenerativeModel":
        self._system_instruction = system_instruction
        self._model = None
        self._get_model()

        return self

    def start_chat(self, args: dict | None = None) -> GenerativeModelChatSession:
        return GeminiChatSession(self, args)

    def ask(self, message: str) -> GenerationResponse:
        response = self._model.generate_content(message)
        return self.parse_generate_content_response(response)

    def parse_generate_content_response(
        self, response: VertexAiGenerationResponse
    ) -> GenerationResponse:
        return GenerationResponse(
            text=response.text,
            finish_reason=(
                FinishReason.MAX_TOKENS
                if response.candidates[0].finish_reason
                == VertexAiFinishReason.MAX_TOKENS
                else (
                    FinishReason.STOP
                    if response.candidates[0].finish_reason == VertexAiFinishReason.STOP
                    else FinishReason.OTHER
                )
            ),
        )


class GeminiChatSession(GenerativeModelChatSession):

    def __init__(self, model: GeminiGenerativeModel, args: dict | None = None):
        self._model = model
        self._chat_session = self._model._model.start_chat(
            history=args.get("history", []) if args is not None else [],
            response_validation=(
                args.get("response_validation", False) if args is not None else True
            ),
        )

    def send_message(self, message: str) -> GenerationResponse:
        response = self._chat_session.send_message(message)
        return self._model.parse_generate_content_response(response)