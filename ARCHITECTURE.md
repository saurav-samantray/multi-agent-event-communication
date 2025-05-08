# Application Architecture

This document outlines the architecture of the Ollama-Powered Multi-Agent System with Kafka.

## Core Components

1.  **User Interface (CLI - `main_cli.py`)**:
    *   The entry point for the user.
    *   Sends user prompts to Kafka.
    *   Listens for and displays the final synthesized response from Kafka.

2.  **Kafka Message Broker**:
    *   The central nervous system for event-based communication.
    *   **Topics Used**:
        *   `user_prompts_topic`: Carries initial prompts from the CLI to the Master Agent.
        *   `agent_tasks_researcher`: Carries research tasks from the Master Agent to the Research Agent.
        *   `agent_tasks_writer`: Carries writing tasks from the Master Agent to the Writing Agent.
        *   `agent_results_topic`: Carries results from worker agents back to the Master Agent.
        *   `final_output_topic`: Carries the final synthesized response from the Master Agent to the CLI.

3.  **Master Agent (`agents/master_agent.py`)**:
    *   The orchestrator of the system.
    *   Consumes from `user_prompts_topic` and `agent_results_topic`.
    *   Produces to `agent_tasks_researcher`, `agent_tasks_writer`, and `final_output_topic`.
    *   Uses Ollama for:
        *   Generating a multi-step task plan from the user's prompt.
        *   Synthesizing the final response from the collected results of worker agents.
    *   Manages the state of ongoing requests and task dependencies (currently in-memory).

4.  **Research Agent (`agents/research_agent.py`)**:
    *   A specialized worker agent.
    *   Consumes tasks from `agent_tasks_researcher`.
    *   Uses Ollama to perform research based on the task description.
    *   Produces its findings to `agent_results_topic`.

5.  **Writing Agent (`agents/writing_agent.py`)**:
    *   Another specialized worker agent.
    *   Consumes tasks (and potentially context from previous tasks) from `agent_tasks_writer`.
    *   Uses Ollama to compose text based on the task description and provided context.
    *   Produces its composed text to `agent_results_topic`.

6.  **Ollama LLM Service**:
    *   The "brain" providing language understanding and generation capabilities.
    *   Accessed by the Master Agent, Research Agent, and Writing Agent for their respective LLM-dependent operations.
    *   Configured via `OLLAMA_BASE_URL` and `OLLAMA_MODEL` in `config.py`.

7.  **Docker Environment (`docker-compose.yml`)**:
    *   Hosts the Kafka message broker (and Zookeeper).
    *   Hosts the Ollama service.
    *   Provides a consistent runtime environment for these backing services.

## High-Level Data Flow

1.  **Prompt Submission**:
    *   User enters a prompt into the **CLI**.
    *   CLI sends the prompt to Kafka's `user_prompts_topic`.

2.  **Task Planning & Dispatch**:
    *   **Master Agent** consumes the prompt from `user_prompts_topic`.
    *   Master Agent queries **Ollama** to break down the prompt into a plan of tasks.
    *   Master Agent sends individual tasks to appropriate Kafka topics (`agent_tasks_researcher` or `agent_tasks_writer`), respecting dependencies.

3.  **Task Execution by Worker Agents**:
    *   **Research Agent** consumes a task from `agent_tasks_researcher`.
        *   It queries **Ollama** to get research information.
        *   It sends the result to `agent_results_topic`.
    *   **Writing Agent** consumes a task from `agent_tasks_writer` (potentially with input data from a previous research task).
        *   It queries **Ollama** to generate the written content.
        *   It sends the result to `agent_results_topic`.

4.  **Result Aggregation & Final Synthesis**:
    *   **Master Agent** consumes results from `agent_results_topic`.
    *   It updates the status of the overall request.
    *   If more tasks are ready (dependencies met), it dispatches them.
    *   Once all tasks for the request are complete, the Master Agent queries **Ollama** again to synthesize a final, coherent response using all gathered information.

5.  **Delivering the Response**:
    *   **Master Agent** sends the final synthesized response to Kafka's `final_output_topic`.
    *   The **CLI** consumes this response and displays it to the user.

## Architecture Diagram

```
+--------------+     1. Prompt     +-----------------------+     2. Plan     +-----------------+     3. Task(s)  +------------------------+
| User via CLI | --------------> | USER_PROMPTS_TOPIC    | --------------> |  Master Agent   | +-------------> | AGENT_TASKS_researcher |
| (main_cli.py)|                 +-----------------------+                 +-------+---------+ |               +------------------------+
+--------------+                        (Kafka)                                    | Ollama (Plan) |                       (Kafka)
       ^                                                                             |               |
       |                                                                             |               +-------------> +------------------------+
       | 8. Final Resp.                                                              |                               | AGENT_TASKS_writer     |
       |                                                                             | 6. Result(s)                  +------------------------+
+-----------------------+                                                              |               (Kafka)         |           |
| FINAL_OUTPUT_TOPIC    | <-------------- 7. Synthesize                              |                               |           |
+-----------------------+   (Master Agent + Ollama)                                  |                               v           v
       (Kafka)                                                                     |      +-----------------+     4. Execute    +----------+
                                                                                     +----> | Research Agent  | ---------------> |  Ollama  |
                                                                                     |      +-----------------+                   +----------+
                                                                                     |               |      (research_agent.py)
                                                                                     |               | 5. Result
                                                                                     |               v
                                                                 +--------------------+
                                                                 | AGENT_RESULTS_TOPIC|
                                                                 +--------------------+
                                                                       (Kafka) ^
                                                                               | 5. Result
                                                                               |      +-----------------+     4. Execute    +----------+
                                                                               +------|  Writing Agent  | ---------------> |  Ollama  |
                                                                                      +-----------------+                   +----------+
                                                                                            (writing_agent.py)

+-----------------------------------------------------------------------------------------------------------------+
| Docker Environment (docker-compose.yml)                                                                         |
|   +----------------------+                            +------------------------------------------------------+  |
|   | Kafka (+Zookeeper)   |                            | Ollama Service (LLM: llama3 by default)              |  |
|   +----------------------+                            +------------------------------------------------------+  |
+-----------------------------------------------------------------------------------------------------------------+
```