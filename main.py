import sys
import webbrowser

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox, QProgressDialog

from app.core.startup_controller import StartupController
from app.UI.main_window import BabuWindow


class BabuApplication:

    def __init__(self):

        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        self.controller = StartupController()

        self.window = None
        self.progress_dialog = None

        self.controller.startup_completed.connect(
            self.open_chat
        )

        self.controller.setup_required.connect(
            self.show_setup_message
        )

        self.controller.progress_updated.connect(
            self.update_setup_progress
        )

        self.controller.startup_failed.connect(
            self.show_error
        )

    def start(self):

        self.controller.start()

        sys.exit(self.app.exec())

    def open_chat(self, agent_service):

        if self.progress_dialog is not None:
            self.progress_dialog.close()
            self.progress_dialog = None

        self.app.setQuitOnLastWindowClosed(True)
        self.window = BabuWindow(agent_service)
        self.window.show()

    def show_setup_message(self, reason):

        if reason == "ollama":

            QMessageBox.warning(
                None,
                "Ollama Required",
                "Ollama is not installed or not running.\n\n"
                "Please install Ollama and start it "
                "before continuing."
            )
            webbrowser.open("https://ollama.com/download")
            self.app.quit()

        elif reason == "model":

            self.progress_dialog = QProgressDialog(
                "Setting up Babu's required GGUF model...",
                None,
                0,
                0
            )
            self.progress_dialog.setWindowTitle("Model Setup")
            self.progress_dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
            self.progress_dialog.setMinimumDuration(0)
            self.progress_dialog.show()

    def update_setup_progress(self, data):

        if self.progress_dialog is None:
            return

        status = data.get("status", "Processing...")
        completed = data.get("completed", 0)
        total = data.get("total", 0)

        self.progress_dialog.setLabelText(status)

        if total > 0:
            self.progress_dialog.setMaximum(100)
            percentage = int((completed / total) * 100)
            self.progress_dialog.setValue(percentage)
        else:
            # Indeterminate progress bar while hashing/uploading
            self.progress_dialog.setMaximum(0)
            self.progress_dialog.setValue(0)

    def show_error(self, message):

        if self.progress_dialog is not None:
            self.progress_dialog.close()
            self.progress_dialog = None

        QMessageBox.critical(
            None,
            "Startup Error",
            f"Babu could not start:\n\n{message}"
        )

        self.app.quit()


if __name__ == "__main__":

    babu = BabuApplication()
    babu.start()