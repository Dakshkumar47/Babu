# Babu
Local AI Desktop Assistant powered by Ollama

Babu is a Windows-based local AI desktop assistant designed to bring conversational AI and practical tool execution to your desktop using locally hosted language models.


## ✨ Features

- **Desktop Interface:** Built using Python and PySide6.
- **Local LLM Integration:** Uses Ollama to run GGUF-based language models locally.
- **Web Search:** Enables the assistant to search the web and retrieve relevant information.
- **System Tools:** Supports interaction with system-level utilities.
- **Shell Tools:** Enables execution of supported shell commands through the assistant.
- **Windows Installer:** Packaged as a Windows executable installer using Inno Setup.

## 📦 Installation

1. Download `Babu-Setup-v1.0.0.exe` from the Assets section in release section.
2. Install Ollama separately if it is not already installed.
3. Download the supported GGUF model using the provided model download instructions.
4. Complete the model setup as described in the installation guide.
5. Start Ollama manually.
6. Launch Babu and start interacting with your local AI assistant.

Refer to the Installation Guide for detailed instructions.

## ⚠️ Important Notes

- Ollama must be installed and running before launching Babu.
- The GGUF model is distributed separately from the application installer.
- Model download and configuration must be completed before using the assistant.
- Tool execution depends on the availability of the relevant system resources and permissions.
- Shell commands can modify your system. Only execute commands you understand.

## 🔧 Technology Stack

- Python
- PySide6
- Ollama
- GGUF
- Inno Setup

## 📋 Known Limitations

- Ollama must be started manually.
- The application requires a separately downloaded and configured language model.
- Performance depends on the selected model and available hardware.

## 🚀 What's Next?

Future development may include:
- Automated model and runtime initialization.
- Improved permission management for tool execution.
- Intelligent request routing.
- Performance evaluation and optimization.

---

**Thank you for trying Babu!**

Your feedback and suggestions are welcome.
