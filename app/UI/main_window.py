"""
Babu desktop UI.

Features:
    - PySide6 chat interface
    - Background agent execution
    - UI status updates
    - Error handling
    - Conversation history
"""

import sys
import traceback
from app.core.agent_service import AgentService

from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QPushButton,
    QFrame,
    QScrollArea,
    QSizePolicy,
)


class AgentWorker(QThread):
    """Runs the agent in a background thread and reports its status."""

    response_ready = Signal(str)
    error_occurred = Signal(str)
    status_updated = Signal(str)

    def __init__(self, agent_service, user_message, history=None):
        super().__init__()
        self.agent_service = agent_service
        self.user_message = user_message
        self.history = history or []

    def run(self):
        try:
            # Indicate that the agent is processing the request.
            self.status_updated.emit("◐ Thinking...")

            response = self.agent_service.get_response(
                self.user_message,
                self.history
            )

            # Send the completed response to the UI.
            self.response_ready.emit(response)

        except Exception as error:
            traceback.print_exc()
            self.error_occurred.emit(str(error))

class MessageInput(QTextEdit):
    """Input widget supporting Enter and Shift+Enter."""

    def __init__(self, send_callback, parent=None):
        super().__init__(parent)

        self.send_callback = send_callback

        self.setPlaceholderText("Ask Babu...")
        self.setFixedHeight(55)
        self.setObjectName("message_input")

    def keyPressEvent(self, event):
        """Enter sends; Shift+Enter inserts a new line."""

        if event.key() in (
            Qt.Key.Key_Return,
            Qt.Key.Key_Enter,
        ):
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                super().keyPressEvent(event)
            else:
                self.send_callback()
        else:
            super().keyPressEvent(event)


class ChatMessage(QWidget):
    """A single message displayed in the conversation."""

    def __init__(self, sender, message, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(5)

        sender_label = QLabel(sender)

        sender_label.setObjectName(
            "user_label" if sender == "You" else "assistant_label"
        )

        message_label = QLabel(message)
        message_label.setWordWrap(True)

        message_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        message_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )

        message_label.setObjectName(
            "user_message" if sender == "You" else "assistant_message"
        )

        layout.addWidget(sender_label)
        layout.addWidget(message_label)


class BabuWindow(QMainWindow):

    def __init__(self, agent_service):
        super().__init__()

        self.agent_service = agent_service

        # Retain the worker object while a request is running.
        self.worker = None

        # Store conversation messages for subsequent requests.
        self.conversation_history = []

        self.setWindowTitle("Babu")
        self.resize(350, 300)
        self.setMinimumSize(350, 300)

        self.setup_ui()
        self.apply_styles()

        self.connection_status.setText("● Connected")

        self.add_message(
            "Babu",
            "Hello! I'm ready to help. What would you like to do?",
        )

    def setup_ui(self):

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 12, 20, 12)
        main_layout.setSpacing(12)

        # ---------------- HEADER ----------------

        header_layout = QHBoxLayout()

        title = QLabel("Babu")
        title.setObjectName("title")

        self.connection_status = QLabel("● Initializing")
        self.connection_status.setObjectName("status")

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.connection_status)

        main_layout.addLayout(header_layout)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setObjectName("separator")

        main_layout.addWidget(separator)

        # ---------------- CHAT AREA ----------------
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.chat_scroll.setObjectName("chat_scroll")

        self.chat_container = QWidget()
        self.chat_container.setObjectName("chat_container")

        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setContentsMargins(10, 5, 10, 5)
        self.chat_layout.setSpacing(8)

        # Keep the messages at the top when there are only a few.
        self.chat_layout.addStretch()

        self.chat_scroll.setWidget(self.chat_container)
        # Track auto-scroll state and react when the scroll area's height actually updates.
        self._auto_scroll = True
        scrollbar = self.chat_scroll.verticalScrollBar()
        scrollbar.rangeChanged.connect(self._on_scroll_range_changed)
        scrollbar.valueChanged.connect(self._on_scroll_value_changed)

        main_layout.addWidget(self.chat_scroll, stretch=1)

        # ---------------- INPUT AREA ----------------

        input_layout = QHBoxLayout()
        input_layout.setSpacing(10)

        self.message_input = MessageInput(self.send_message)

        self.send_button = QPushButton("➤")
        self.send_button.setFixedSize(50, 50)
        self.send_button.setObjectName("send_button")
        self.send_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_button.clicked.connect(self.send_message)

        input_layout.addWidget(self.message_input, stretch=1)
        input_layout.addWidget(self.send_button)

        main_layout.addLayout(input_layout)

        # ---------------- FOOTER ----------------

        footer_layout = QHBoxLayout()

        self.model_status = QLabel("Model: Qwen 4B")
        self.model_status.setObjectName("footer")

        self.tool_status = QLabel("Tools: Configured")
        self.tool_status.setObjectName("footer")

        self.agent_status = QLabel("● Ready")
        self.agent_status.setObjectName("footer")

        footer_layout.addWidget(self.model_status)
        footer_layout.addStretch()
        footer_layout.addWidget(self.tool_status)
        footer_layout.addSpacing(20)
        footer_layout.addWidget(self.agent_status)

        main_layout.addLayout(footer_layout)

    # ---------------- MESSAGE HANDLING ----------------

    def add_message(self, sender, message):
        """Add an individual message to the scrollable chat area."""

        self._auto_scroll = True
        message_widget = ChatMessage(sender, message)

        # Insert before the final stretch.
        self.chat_layout.insertWidget(
            self.chat_layout.count() - 1,
            message_widget,
        )

    def _on_scroll_range_changed(self, _min_val, max_val):
        """Scroll to the bottom once Qt finishes computing the new layout height."""

        if self._auto_scroll:
            self.chat_scroll.verticalScrollBar().setValue(max_val)

    def _on_scroll_value_changed(self, value):
        """Pause auto-scroll if the user manually scrolls up to read older messages."""

        scrollbar = self.chat_scroll.verticalScrollBar()
        self._auto_scroll = value >= scrollbar.maximum() - 10

    # ---------------- AGENT INTEGRATION ----------------

    def send_message(self):
        """Submit the user's message to the background worker."""

        # Prevent concurrent agent calls.
        if self.worker is not None and self.worker.isRunning():
            return

        user_message = self.message_input.toPlainText().strip()

        if not user_message:
            return

        # Display the user message immediately.
        self.add_message("You", user_message)
        self.message_input.clear()

        # Store the new user message in conversation history.
        self.conversation_history.append({
            "role": "user",
            "content": user_message,
        })

        # Update the interface while the model is running.
        self.agent_status.setText("◐ Thinking")
        self.send_button.setEnabled(False)
        self.message_input.setEnabled(False)

        # Pass only the earlier messages as history.
        # AgentService adds the current message itself.
        previous_history = self.conversation_history[:-1]

        # Create a worker for this request.
        self.worker = AgentWorker(
            agent_service=self.agent_service,
            user_message=user_message,
            history=previous_history,
        )

        # Connect worker signals to UI methods.
        self.worker.response_ready.connect(self.handle_response)
        self.worker.error_occurred.connect(self.handle_error)
        self.worker.status_updated.connect(self.update_status)

        # Start inference without blocking the UI.
        self.worker.start()

    def handle_response(self, response):
        """Display the agent response and save it in history."""

        self.add_message("Babu", response)

        self.conversation_history.append({
            "role": "assistant",
            "content": response,
        })

        self.finish_request()

    def handle_error(self, error_message):
        """Display an error if the agent call fails."""

        self.add_message(
            "Babu",
            f"Sorry, something went wrong:\n{error_message}",
        )

        self.finish_request()

    def update_status(self, status):
        """
        Update the UI status labels when the worker reports progress.

        This method runs in the UI thread through Qt's signal-slot
        mechanism, keeping the interface responsive.
        """

        # Update the footer status.
        self.agent_status.setText(status)

    def finish_request(self):
        self.agent_status.setText("● Ready")
        self.send_button.setEnabled(True)
        self.message_input.setEnabled(True)
        self.message_input.setFocus()

        if self.worker is not None:
            self.worker.finished.connect(self.clear_worker_reference)

    def clear_worker_reference(self):
        """Release the reference to a completed worker."""

        worker = self.worker
        self.worker = None

        if worker is not None:
            worker.deleteLater()

    # ---------------- STYLING ----------------

    def apply_styles(self):

        self.setStyleSheet("""
            QMainWindow {
                background-color: #181818;
            }

            QWidget {
                color: #E6E6E6;
                font-family: "Segoe UI";
                font-size: 14px;
            }

            QLabel#title {
                font-size: 19px;
                font-weight: bold;
                color: #F2F2F2;
            }

            QLabel#status {
                color: #999999;
                font-size: 12px;
            }

            QFrame#separator {
                color: #303030;
            }

            QScrollArea#chat_scroll {
                background-color: #181818;
                border: none;
            }

            QWidget#chat_container {
                background-color: #181818;
            }

            QLabel#user_label {
                color: #80B9D1;
                font-size: 12px;
                font-weight: bold;
            }

            QLabel#assistant_label {
                color: #F2F2F2;
                font-size: 12px;
                font-weight: bold;
            }

            QLabel#user_message {
                background-color: #252525;
                border-radius: 8px;
                padding: 10px;
                color: #E6E6E6;
            }

            QLabel#assistant_message {
                background-color: transparent;
                padding: 4px 0;
                color: #E6E6E6;
            }

            QTextEdit#message_input {
                background-color: #252525;
                border: 1px solid #383838;
                border-radius: 10px;
                padding: 10px;
                color: #E6E6E6;
                selection-background-color: #315B70;
            }

            QTextEdit#message_input:focus {
                border: 1px solid #527F96;
            }

            QTextEdit#message_input:disabled {
                color: #777777;
                background-color: #202020;
            }

            QPushButton#send_button {
                background-color: #315B70;
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 22px;
                font-weight: bold;
            }

            QPushButton#send_button:hover {
                background-color: #3C718A;
            }

            QPushButton#send_button:disabled {
                background-color: #303030;
                color: #777777;
            }

            QLabel#footer {
                color: #929292;
                font-size: 11px;
            }
        """)


if __name__ == "__main__":

    app = QApplication(sys.argv)

    # ---------------------------------------------------------
    # INITIALIZE YOUR EXISTING AGENT HERE.
    #
    # Import the initialized agent from the module in which
    # you currently create it. Do not create another LLM or
    # another tool registry just for the UI.
    #
    # Example:
    # ---------------------------------------------------------

    from app.llm.model import agent
    # raise RuntimeError(
    #     "Import your existing initialized agent and pass it "
    #     "to AgentService before launching the UI."
    # )

    service = AgentService(agent)
    window = BabuWindow(service)
    window.show()
    sys.exit(app.exec())
