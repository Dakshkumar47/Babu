import hashlib
import json
import sys
import re
from pathlib import Path
import requests
from app.llm.model import MODEL_NAME


class ModelSetupService:

    def __init__(self):
        self.base_url = "http://localhost:11434"
        # If running as compiled .exe, use the folder where Babu.exe is located
        if getattr(sys, "frozen", False):
            self.project_dir = Path(sys.executable).resolve().parent
        else:
            self.project_dir = Path(__file__).resolve().parents[2]

        self.gguf_path = self.project_dir / "models" / "qwen3-4b-q4_k_m.gguf"
        self.modelfile_path = self.project_dir / "models" / "Modelfile"

    def check_ollama(self):
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            return {"status": "success", "message": "Ollama is running."}
        except requests.exceptions.ConnectionError:
            return {"status": "error", "message": "Ollama is not running."}
        except requests.exceptions.Timeout:
            return {"status": "error", "message": "Ollama connection timed out."}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "message": str(e)}

    def get_installed_models(self):
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=10)
            response.raise_for_status()
            data = response.json()
            return {"status": "success", "models": data.get("models", [])}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "message": str(e)}

    def is_model_installed(self):
        result = self.get_installed_models()
        if result["status"] == "error":
            return result

        required_model = MODEL_NAME
        for model in result["models"]:
            installed_name = model.get("name", "")
            if installed_name in (required_model, f"{required_model}:latest"):
                return {
                    "status": "success",
                    "installed": True,
                    "model_name": installed_name,
                }

        return {
            "status": "success",
            "installed": False,
            "model_name": required_model,
        }

    def validate_gguf(self):
        try:
            if not self.gguf_path.exists():
                return {"status": "error", "message": "Babu's GGUF model file is missing."}
            if not self.gguf_path.is_file():
                return {"status": "error", "message": "The model path is not a file."}
            if self.gguf_path.suffix.lower() != ".gguf":
                return {"status": "error", "message": "Invalid model file format."}
            if self.gguf_path.stat().st_size == 0:
                return {"status": "error", "message": "The model file is empty."}

            with open(self.gguf_path, "rb") as file:
                signature = file.read(4)

            if signature != b"GGUF":
                return {"status": "error", "message": "The selected model is not a valid GGUF file."}

            return {
                "status": "success",
                "message": "GGUF model validated successfully.",
                "path": str(self.gguf_path),
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def calculate_sha256(self):
        sha256 = hashlib.sha256()
        with open(self.gguf_path, "rb") as file:
            while chunk := file.read(1024 * 1024):
                sha256.update(chunk)
        return sha256.hexdigest()

    def parse_modelfile_config(self):
        """
        Extracts SYSTEM, TEMPLATE, and PARAMETER directives from Modelfile
        for Ollama's /api/create payload.
        """
        if not self.modelfile_path.exists():
            return {"status": "error", "message": "Modelfile is missing."}

        try:
            content = self.modelfile_path.read_text(encoding="utf-8")
            config = {}
            # Extract TEMPLATE block if present
            tpl_match = re.search(
                r'(?im)^TEMPLATE\s+(?:"""(.*?)"""|"(.*?)"|(.+))$',
                content,
                re.DOTALL,
            )
            if tpl_match:
                config["template"] = next(g for g in tpl_match.groups() if g is not None).strip()

            # Extract PARAMETER key-value pairs
            parameters = {}
            for match in re.finditer(r"(?im)^PARAMETER\s+(\S+)\s+(.+)$", content):
                key, val = match.group(1).strip(), match.group(2).strip().strip('"')
                
                # Ollama requires "stop" to be an array of strings
                if key == "stop":
                    parameters.setdefault("stop", []).append(val)
                elif val.lower() in ("true", "false"):
                    parameters[key] = val.lower() == "true"
                else:
                    try:
                        parameters[key] = float(val) if "." in val else int(val)
                    except ValueError:
                        parameters[key] = val

            if parameters:
                config["parameters"] = parameters

            return {"status": "success", "config": config}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def create_model(self, progress_callback=None):
        """
        Uploads Babu's GGUF file to Ollama via POST /api/blobs/:digest
        and creates the model defined by MODEL_NAME.
        """
        try:
            # Step 1: Validate GGUF
            validation = self.validate_gguf()
            if validation["status"] == "error":
                return validation

            if progress_callback:
                progress_callback({"status": "Calculating model checksum..."})

            # Step 2: Calculate SHA256
            file_hash = self.calculate_sha256()
            digest = f"sha256:{file_hash}"
            blob_url = f"{self.base_url}/api/blobs/{digest}"

            # Step 3: Check if blob already exists; upload via POST if missing
            head_resp = requests.head(blob_url, timeout=10)

            if head_resp.status_code != 200:
                if progress_callback:
                    progress_callback({"status": "Uploading GGUF model..."})

                with open(self.gguf_path, "rb") as file:
                    response = requests.post(
                        blob_url,
                        data=file,
                        headers={"Content-Type": "application/octet-stream"},
                        timeout=(10, 600),
                    )

                if response.status_code not in (200, 201):
                    return {
                        "status": "error",
                        "message": f"GGUF upload failed ({response.status_code}): {response.text}",
                    }
            else:
                if progress_callback:
                    progress_callback({"status": "GGUF blob already cached in Ollama..."})

            # Step 4: Parse Modelfile settings
            modelfile_result = self.parse_modelfile_config()
            if modelfile_result["status"] == "error":
                return modelfile_result

            # Step 5: Prepare model creation request using MODEL_NAME
            payload = {
                "model": MODEL_NAME,
                "files": {
                    self.gguf_path.name: digest
                },
                "stream": True,
                **modelfile_result["config"],
            }

            if progress_callback:
                progress_callback({"status": f"Creating model '{MODEL_NAME}'..."})

            # Step 6: Create model
            with requests.post(
                f"{self.base_url}/api/create",
                json=payload,
                stream=True,
                timeout=(10, 600),
            ) as response:

                if response.status_code != 200:
                    return {
                        "status": "error",
                        "message": f"Model creation failed: {response.text}",
                    }

                for line in response.iter_lines():
                    if not line:
                        continue

                    data = json.loads(line.decode("utf-8"))

                    if "error" in data:
                        return {"status": "error", "message": data["error"]}

                    if progress_callback:
                        progress_callback({
                            "status": data.get("status", "Creating model..."),
                            "completed": data.get("completed", 0),
                            "total": data.get("total", 0),
                        })

            # Step 7: Verify model registration
            verification = self.is_model_installed()
            if verification["status"] == "error":
                return verification

            if not verification["installed"]:
                return {
                    "status": "error",
                    "message": "Model creation finished, but verification failed.",
                }

            return {
                "status": "success",
                "message": "Babu's model was created successfully.",
                "model_name": MODEL_NAME,
            }

        except requests.exceptions.Timeout:
            return {"status": "error", "message": "Ollama request timed out."}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "message": str(e)}
        except Exception as e:
            return {"status": "error", "message": str(e)}