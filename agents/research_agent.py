# /full/path/to/project/ollama_multi_agent_kafka/agents/research_agent.py
import json
import time
from utils.kafka_utils import create_producer, create_consumer
from utils.ollama_utils import get_ollama_response
from config import AGENT_TASKS_PREFIX, AGENT_RESULTS_TOPIC, AGENT_RESEARCHER

AGENT_TYPE = AGENT_RESEARCHER
TASK_TOPIC = f"{AGENT_TASKS_PREFIX}{AGENT_TYPE}"

def process_task(task_data):
    print(f"[{AGENT_TYPE.upper()}_AGENT] Received task: {task_data['task_id']} - {task_data['description']}")
    
    prompt = f"""You are a specialized research agent. Your task is to find information based on the given description.
Research Task: "{task_data['description']}"
Provide a concise and factual answer to this research task.
If the task is to find specific data, provide that data. If it's a question, answer it.
"""
    try:
        result = get_ollama_response(prompt)
        print(f"[{AGENT_TYPE.upper()}_AGENT] Task {task_data['task_id']} completed. Result: {result[:100]}...")
        return {"status": "completed", "result": result}
    except Exception as e:
        print(f"[{AGENT_TYPE.upper()}_AGENT] Error processing task {task_data['task_id']}: {e}")
        return {"status": "failed", "error_message": str(e)}

def main():
    print(f"[{AGENT_TYPE.upper()}_AGENT] Starting...")
    consumer = create_consumer(TASK_TOPIC, group_id=f"{AGENT_TYPE}_agent_group")
    producer = create_producer()
    print(f"[{AGENT_TYPE.upper()}_AGENT] Listening for tasks on {TASK_TOPIC}")

    try:
        while True:  # Keep the agent alive and polling
            for message in consumer: # This loop will yield messages or finish after consumer_timeout_ms
                if message: # Ensure a message was actually received
                    task_data = message.value
                    # Basic validation
                    if not all(k in task_data for k in ["request_id", "task_id", "description"]):
                        print(f"[{AGENT_TYPE.upper()}_AGENT] Received malformed task: {task_data}")
                        continue

                    processed_result = process_task(task_data)
                    
                    response_payload = {**task_data, **processed_result} # Merge original task data with results
                    producer.send(AGENT_RESULTS_TOPIC, value=response_payload)
                    producer.flush()
            # The 'for message in consumer' loop has finished due to timeout.
            # The 'while True' loop will bring execution back to re-enter the 'for' loop,
            # effectively re-polling Kafka.
            # A small sleep here is optional if consumer_timeout_ms is very low, to prevent a tight loop.
            # With consumer_timeout_ms=1000, it's generally not strictly needed.
            # time.sleep(0.01) # Example: if you want to add a tiny pause
    except KeyboardInterrupt:
        print(f"[{AGENT_TYPE.upper()}_AGENT] Shutting down...")
    finally:
        if consumer: consumer.close()
        if producer: producer.close()

if __name__ == "__main__":
    main()