# Ollama-Powered Multi-Agent System with Kafka

This project demonstrates a multi-LLM agent application where a master agent orchestrates tasks among specialized worker agents using Kafka for event-based communication. All LLM interactions are powered by Ollama.

## Core Components

*   **Master Agent**:
    *   Receives user prompts.
    *   Uses an LLM (via Ollama) to devise a plan of tasks.
    *   Dispatches tasks to worker agents via Kafka.
    *   Collects results from worker agents.
    *   Uses an LLM (via Ollama) to synthesize the final response.
*   **Worker Agents**:
    *   `ResearchAgent`: Specializes in performing research tasks using Ollama.
    *   `WritingAgent`: Specializes in composing text based on instructions and provided context (often from the `ResearchAgent`) using Ollama.
*   **Kafka**: Acts as the message bus for asynchronous communication between the Master Agent and Worker Agents.
*   **Ollama**: Provides the local LLM capabilities for all agents.

## Prerequisites

*   **Docker and Docker Compose**: For running Kafka and Ollama.
*   **Python 3.8+**: For running the agents and CLI.
*   **Ollama**: Installed and running. You can run it locally or use the provided `docker-compose.yml`.
    *   An Ollama model pulled (e.g., `llama3`, `mistral`). The default is `llama3` (see `config.py`).

## Project Structure

```
ollama_multi_agent_kafka/
├── agents/
│   ├── __init__.py
│   ├── master_agent.py
│   ├── research_agent.py
│   └── writing_agent.py
├── utils/
│   ├── __init__.py
│   ├── kafka_utils.py
│   └── ollama_utils.py
├── .gitignore
├── config.py
├── docker-compose.yml
├── main_cli.py
├── README.md
├── requirements.txt
└── run_agents.py
```

## Setup

1.  **Clone the repository (if applicable) or ensure all files are in place.**

2.  **Configure Ollama**:
    *   Ensure Ollama is running. If using the `docker-compose.yml`, Ollama will be started as a service.
    *   Pull your desired LLM model. For example, if Ollama is running in Docker:
        ```bash
        docker exec -it ollama ollama pull llama3
        ```
    *   Update `OLLAMA_MODEL` in `/full/path/to/project/ollama_multi_agent_kafka/config.py` if you are using a different model.
    *   Ensure `OLLAMA_BASE_URL` in `/full/path/to/project/ollama_multi_agent_kafka/config.py` points to your Ollama instance (default is `http://localhost:11434`).

3.  **Start Kafka and Ollama (using Docker Compose)**:
    Navigate to the project root directory (`/full/path/to/project/ollama_multi_agent_kafka/`) and run:
    ```bash
    docker-compose up -d
    ```
    This will start Zookeeper, Kafka, and the Ollama service.

4.  **Install Python Dependencies**:
    Create a virtual environment (recommended) and install the required packages:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    pip install -r /full/path/to/project/ollama_multi_agent_kafka/requirements.txt
    ```

## How to Run

1.  **Run the Agents**:
    Open a terminal, navigate to the project root (`/full/path/to/project/ollama_multi_agent_kafka/`), and run:
    ```bash
    python /full/path/to/project/ollama_multi_agent_kafka/run_agents.py
    ```
    You should see logs indicating that the Master, Research, and Writing agents have started and are connected to Kafka.

2.  **Interact with the System via CLI**:
    Open a *new* terminal, navigate to the project root, and run:
    ```bash
    python /full/path/to/project/ollama_multi_agent_kafka/main_cli.py
    ```
    You'll be prompted to enter your request. For example:
    ```
    Enter your prompt (or 'exit' to quit): Tell me about the history of Python and then write a short poem about it.
    ```
    Observe the agent logs in the first terminal to see the task breakdown and execution. The final synthesized response will appear in the CLI terminal.

## Configuration

Key configurations can be found in `/full/path/to/project/ollama_multi_agent_kafka/config.py`:
*   `KAFKA_BROKER`: Kafka broker address.
*   `OLLAMA_BASE_URL`: Base URL for the Ollama API.
*   `OLLAMA_MODEL`: The Ollama model to be used by the agents.
*   Kafka Topics: Names for various topics used for communication.

## Stopping the Application

1.  Press `Ctrl+C` in the `main_cli.py` terminal to stop the CLI.
2.  Press `Ctrl+C` in the `run_agents.py` terminal to stop the agents.
3.  To stop Kafka and Ollama services (if started with Docker Compose):
    ```bash
    docker-compose down
    ```

## Future Enhancements

*   More robust error handling and retry mechanisms.
*   Persistent storage for task states (e.g., Redis, database) instead of in-memory.
*   Web interface instead of CLI.
*   Addition of more specialized agents (e.g., CodeExecutionAgent, FileAccessAgent).
*   Dynamic agent discovery.
*   Security considerations for agent communication and LLM interactions.