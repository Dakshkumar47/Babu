from typing import Annotated
from langchain_community.tools import ShellTool
from langchain.tools import tool


@tool
def simple_shell_tool(
    cmd: Annotated[
        str,
        "A single read-only shell command, or multiple commands joined with '&&'."
    ]
) -> dict:
    """Execute safe, read-only system and environment commands (such as checking Python/pip versions, environment variables, system info, or running scripts). Do NOT use this tool to list directories, search files, or read files—use the dedicated file tools instead. Never run destructive or file-modifying commands."""
    try:
        shell_command_executor = ShellTool()
        tool_output = shell_command_executor.invoke(cmd)

        return {
            "status": "success",
            "output": tool_output
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

