"""
Agent service adapter.

Purpose:
    Provide a simple interface between the PySide6 UI and the
    existing Jarvis agent.

Important:
    This module should NOT create a second model or a second agent.
    Import your existing initialized agent instead.
"""

# from app.llm.model import agent


class AgentService:
    """Provides a UI-independent interface to the Jarvis agent."""

    def __init__(self, agent_instance):
        # Receive the existing agent instead of constructing
        # another model or agent inside the UI.
        self.agent = agent_instance

    def get_response(self, user_message, history=None):
        """
        Send a message to the existing agent and return its response.

        Args:
            user_message: The latest message entered by the user.
            history: Earlier conversation messages, if supported
                     by the existing agent.

        Returns:
            The assistant's response as a string.
        """

        # Build the message list expected by a LangChain agent
        # using the standard messages-based interface.
        messages = []

        # Include previous conversation messages when available.
        if history:
            messages.extend(history)

        # Add the current user message.
        messages.append({
            "role": "user",
            "content": user_message,
        })

        # Invoke the existing agent.
        result = self.agent.invoke({
            "messages": messages,
        })
        # LangChain agents commonly return a dictionary containing
        # the conversation under the "messages" key.
        response_messages = result.get("messages", [])

        # Find the latest assistant response.
        for message in reversed(response_messages):
            # Tool messages are not final assistant responses.
            if getattr(message, "type", "") == "ai":
                content = getattr(message, "content", "")

                # Handle ordinary text responses.
                if isinstance(content, str) and content.strip():
                    return content

                # Some models return structured content blocks.
                if isinstance(content, list):
                    text_parts = []

                    for block in content:
                        if isinstance(block, dict):
                            text = block.get("text")

                            if text:
                                text_parts.append(text)

                    if text_parts:
                        return "\n".join(text_parts)

        # Avoid silently displaying an empty message.
        return "The agent completed the request but returned no text."

# caller = AgentService(agent)
# response = caller.get_response('list down all the files in desktop folder')
# print(response)