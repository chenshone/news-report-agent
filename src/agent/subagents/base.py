"""SubAgent base utilities for creating structured runnables."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig, RunnableLambda


def create_structured_runnable(
    model: Any,
    output_schema: type,
    system_prompt: str,
) -> RunnableLambda:
    """
    Create a Runnable with structured output using Pydantic schema.

    Args:
        model: LangChain chat model.
        output_schema: Pydantic model class for output validation.
        system_prompt: System prompt for the model.

    Returns:
        A callable Runnable.
    """
    structured_model = model.with_structured_output(output_schema)

    def invoke_fn(state: dict, config: RunnableConfig | None = None) -> dict:
        messages = state.get("messages", [])

        full_messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt}
        ]

        for msg in messages:
            if isinstance(msg, HumanMessage):
                full_messages.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                full_messages.append({"role": "assistant", "content": msg.content})
            elif isinstance(msg, dict):
                full_messages.append(msg)

        result = structured_model.invoke(full_messages, config=config)

        result_str = (
            result.model_dump_json(indent=2)
            if hasattr(result, "model_dump_json")
            else str(result)
        )

        return {"messages": [*messages, AIMessage(content=result_str)]}

    return RunnableLambda(invoke_fn)


__all__ = ["create_structured_runnable"]

