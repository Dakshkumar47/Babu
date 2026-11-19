from .system_tools import (
    search_file,
    read_file,
    list_directory,
    get_file_info,
    get_basic_directory_path
)
from .web_tools import web_search_tool,browse_webpage_tool
from .shell_tools import simple_shell_tool

TOOLS = [
    search_file,
    read_file,
    list_directory,
    get_file_info,
    get_basic_directory_path,
    web_search_tool,
    browse_webpage_tool,
    simple_shell_tool
]

TOOLS_MAP = {
    'search_file':search_file,
    'read_file':read_file,
    'list_directory':list_directory,
    'get_file_info':get_file_info,
    'get_basic_directory_path':get_basic_directory_path,
    'web_search_tool':web_search_tool,
    'browse_webpage_tool':browse_webpage_tool,
    'simple_shell_tool':simple_shell_tool
}


