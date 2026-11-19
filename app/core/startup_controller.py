from PySide6.QtCore import QObject, Signal, QThread

from app.core.model_setup_service import ModelSetupService
from app.core.agent_service import AgentService
from app.llm.model import create_babu_agent


class StartupWorker(QThread):

    startup_completed = Signal(object)
    startup_failed = Signal(str)
    setup_required = Signal(str)
    progress_updated = Signal(dict)

    def __init__(self):
        super().__init__()
        self.setup_service = ModelSetupService()

    def run(self):

        # Step 1: Check Ollama
        ollama_result = self.setup_service.check_ollama()

        if ollama_result["status"] == "error":
            self.setup_required.emit("ollama")
            return

        # Step 2: Check required model
        model_result = self.setup_service.is_model_installed()

        if model_result["status"] == "error":
            self.startup_failed.emit(model_result["message"])
            return

        # Step 2b: Create the model automatically if not installed
        if not model_result["installed"]:
            self.setup_required.emit("model")

            create_result = self.setup_service.create_model(
                progress_callback=self.progress_updated.emit
            )

            if create_result["status"] == "error":
                self.startup_failed.emit(create_result["message"])
                return

        # Step 3: Initialize agent
        try:
            agent = create_babu_agent()

            # Step 4: Initialize AgentService
            agent_service = AgentService(agent)

            self.startup_completed.emit(agent_service)

        except Exception as e:
            self.startup_failed.emit(str(e))


class StartupController(QObject):

    startup_completed = Signal(object)
    setup_required = Signal(str)
    startup_failed = Signal(str)
    progress_updated = Signal(dict)

    def __init__(self):
        super().__init__()
        self.worker = None

    def start(self):

        self.worker = StartupWorker()

        self.worker.startup_completed.connect(
            self.startup_completed.emit
        )

        self.worker.setup_required.connect(
            self.setup_required.emit
        )

        self.worker.startup_failed.connect(
            self.startup_failed.emit
        )

        self.worker.progress_updated.connect(
            self.progress_updated.emit
        )

        self.worker.start()