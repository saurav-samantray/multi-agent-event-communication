# config.py

# Kafka Configuration
KAFKA_BROKER = "localhost:9092"

# Ollama Configuration
OLLAMA_BASE_URL = "http://localhost:11434" # Ollama client uses this
OLLAMA_MODEL = "llama3:8b"  # Change this to your preferred model, e.g., "mistral"

# Kafka Topics
USER_PROMPT_TOPIC = "user_prompts_topic"

AGENT_TASKS_PREFIX = "agent_tasks_" # e.g., agent_tasks_researcher
AGENT_RESULTS_TOPIC = "agent_results_topic"

FINAL_OUTPUT_TOPIC = "final_output_topic"

# Agent types (must match agent filenames for topic generation if used that way)
AGENT_RESEARCHER = "researcher"
AGENT_WRITER = "writer"