from langchain.tools import tool
from pypdf import PdfReader
import pathlib
import json
import csv
import os


def _find_matching_files(file_name: str, base_path: pathlib.Path) -> list[dict]:
    """Helper to recursively find files matching file_name while skipping restricted folders."""
    matches = []
    if not (base_path.exists() and base_path.is_dir()):
        return matches

    for root, dirs, files in os.walk(base_path):
        # Skip hidden/system directories for speed and to avoid PermissionError
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in {"AppData", "node_modules", "__pycache__"}]
        for f in files:
            if file_name.lower() in f.lower():
                full_path = pathlib.Path(root) / f
                matches.append({
                    "name": f,
                    "path": str(full_path)
                })
    return matches


@tool
def search_file(file_name: str, directory: str = "") -> dict:
    """Search recursively for files whose names contain the specified search term. Use this when the user wants to locate a file on their computer. Leave directory empty to search the user's home folder (Desktop, Documents, Downloads, OneDrive)."""
    try:
        base_path = pathlib.Path(directory) if directory.strip() else pathlib.Path.home()
        if directory.strip().lower() == "c:":
            base_path = pathlib.Path("C:\\")

        if not (base_path.exists() and base_path.is_dir()):
            return {"status": "error", "error": f"Directory does not exist: {base_path}"}

        matches = _find_matching_files(file_name, base_path)

        return {
            "status": "success",
            "matches": matches[:20],
            "total_found": len(matches)
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@tool
def read_file(file_path: str) -> dict:
    """Read and return the contents of a file (.pdf, .txt, .md, .py, .log, .csv, .json). Accepts either a full path OR just a file name (e.g. 'resume.pdf'); if only a file name is given, it automatically searches the user's folders."""
    formatted_path = pathlib.Path(file_path.strip().strip('"').strip("'"))

    try:
        # If the exact path does not exist, automatically search the user's home folder (covers Desktop, Downloads, Documents, OneDrive)
        if not (formatted_path.exists() and formatted_path.is_file()):
            matches = _find_matching_files(formatted_path.name, pathlib.Path.home())
            if len(matches) == 1:
                formatted_path = pathlib.Path(matches[0]["path"])
            elif len(matches) > 1:
                return {
                    "status": "multiple_matches",
                    "message": "Multiple files matched that name. Ask the user which one to read or call read_file with the exact path.",
                    "matches": matches[:10]
                }
            else:
                return {
                    "status": "error",
                    "error": f"File '{file_path}' was not found anywhere in {pathlib.Path.home()}."
                }

        file_type = formatted_path.suffix.lower()
        if file_type in [".txt", ".md", ".py", ".log"]:
            file_type = ".text"

        content = []
        match file_type:
            case ".csv":
                with open(formatted_path, "r", encoding="utf-8", errors="replace") as file:
                    content = list(csv.reader(file))
            case ".json":
                with open(formatted_path, "r", encoding="utf-8", errors="replace") as file:
                    content = json.load(file)
            case ".text":
                with open(formatted_path, "r", encoding="utf-8", errors="replace") as file:
                    content = file.read()
            case ".pdf":
                pdf_reader = PdfReader(str(formatted_path))
                content = [page.extract_text() or "" for page in pdf_reader.pages]
            case _:
                return {"status": "error", "error": f"Unsupported file type: {formatted_path.suffix}"}

        return {
            "status": "success",
            "resolved_path": str(formatted_path),
            "content": content
        }

    except Exception as e:
        return {"status": "error", "error": str(e)}
        

@tool
def list_directory(directory_path:str) -> dict :
    """List the immediate contents of a specified directory. Returns the names, full paths, and types (file or directory) of items directly inside the given directory. This tool does NOT search recursively and does NOT return the contents of files or nested directories. Use this when the user wants to see what is directly inside a known directory."""

    root_directory_path = pathlib.Path(directory_path)
    items = []

    try:
        if root_directory_path.exists() and root_directory_path.is_dir():
            for item_path in root_directory_path.glob(r"*"):
                file_type = 'file'
                if item_path.is_dir():
                    file_type = 'directory'

                item = {'name':item_path.name,
                        'path':str(item_path),
                        'type':file_type}
                items.append(item)
            return {'status':'success',
                    'items':items}
        
        else:
            return {'status':'error',
                    'error':'the path does not exists'}

    except PermissionError:
        return {'status':'error',
                'error':'permission denied to access this directory'}

    except Exception as e:
        return {'status':'error',
                'error':str(e)}

@tool
def get_file_info(directory_path_arg:str) -> dict:
    """Get metadata about a specific file or directory when its path is known. Returns the name, type, full path, size, creation time, and last modification time. Use this when the user asks about file properties, file size, creation date, modification date, or whether a path refers to a file or directory. Do not use this tool to search for files."""

    try:
        directory_path = pathlib.Path(directory_path_arg)

        if directory_path.exists():
            file_name = directory_path.name
            file_type = 'directory' if directory_path.is_dir() else "file"
            file_path = str(directory_path)
            file_size = directory_path.stat().st_size
            file_creation_time = directory_path.stat().st_ctime
            file_modification_time = directory_path.stat().st_mtime

            metadata = {'file_name':file_name,
                        'file_type':file_type,
                        'file_path':file_path,
                        'file_size':file_size,
                        'file_creation_time':file_creation_time,
                        'file_modification_time':file_modification_time}

            return {'status':'success',
                    'metadata':metadata}

        else:
            return {'status':'error',
                    'error':'path does not exist'}

    except Exception as e:
        return {'status':'error',
                'error':str(e)}

    
@tool
def get_basic_directory_path(directory: str) -> dict:
    """Resolve the full filesystem path of a standard user directory (desktop, downloads, documents, pictures, music, videos)."""
    folder = directory.strip().lower().removeprefix("onedrive/")
    user_home = pathlib.Path.home()
    onedrive = os.environ.get("OneDrive")

    valid_folders = {"desktop", "downloads", "documents", "pictures", "music", "videos"}
    if folder not in valid_folders:
        return {"status": "error", "error": f"Unsupported directory: {directory}"}

    capitalized = folder.capitalize()
    candidates = []
    if onedrive:
        candidates.append(pathlib.Path(onedrive) / capitalized)
    candidates.append(user_home / capitalized)

    for path in candidates:
        if path.exists():
            return {"status": "success", "directory": folder, "path": str(path)}

    return {"status": "error", "error": f"Could not find path for '{directory}'"}
# print(list_directory.invoke(r"C:\Users\LENOVO\OneDrive\Desktop"))