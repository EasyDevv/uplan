from litellm import completion
from uplan.ui.state import AppState


class LLMService:
    async def process_request(self):
        """Process a request using the LLM service.

        Returns:
            str: The stream ID for tracking the response
        """
        state = AppState.get_instance()

        # Construct full model identifier for liteLLM
        model_identifier = f"{state.provider}/{state.model}"

        # Create liteLLM compatible request
        response = await completion(
            model=model_identifier,
            messages=[{"role": "user", "content": "Your prompt here"}],
            stream=True,
        )

        # Process response and return stream ID
        return response.get("stream_id")
