# /full/path/to/project/ollama_multi_agent_kafka/main_cli.py
import uuid
import json
import time
from utils.kafka_utils import create_producer, create_consumer
from config import KAFKA_BROKER, USER_PROMPT_TOPIC, FINAL_OUTPUT_TOPIC

def send_prompt(producer, topic, request_id, prompt_text):
    message = {"request_id": request_id, "prompt": prompt_text}
    producer.send(topic, value=message)
    producer.flush()
    print(f"Sent prompt (Request ID: {request_id}): {prompt_text}")

def listen_for_response(consumer, request_id, timeout_seconds=10000):
    print(f"Waiting for final response for Request ID: {request_id} (timeout: {timeout_seconds}s)...")
    start_time = time.time()
    poll_count = 0

    while time.time() - start_time < timeout_seconds:
        try:
            poll_count += 1
            # print(f"[CLI DEBUG] Polling Kafka... Attempt: {poll_count}, Time elapsed: {time.time() - start_time:.2f}s") # Uncomment for verbose polling log

            # Poll Kafka for messages.
            # The timeout_ms here is for the poll() call itself, not the overall timeout_seconds.
            # We'll poll for up to 1 second in each iteration of this while loop.
            records = consumer.poll(timeout_ms=1000) # Returns a dict: {TopicPartition: [messages]}

            if not records:
                # No messages received in this poll interval, continue the while loop
                # to check overall timeout and poll again.
                # print(f"[CLI DEBUG] No records in poll attempt {poll_count}.") # Uncomment for verbose polling log
                continue

            for tp, messages_in_partition in records.items():
                for message_obj in messages_in_partition:
                    # message_obj is a ConsumerRecord; its .value is already deserialized by the consumer.
                    response_data = message_obj.value
                    if response_data.get("request_id") == request_id:
                        print("\n===== Final Response =====")
                        print(response_data.get("final_response"))
                        print("==========================")
                        # consumer.commit() # Optional: Explicit commit if auto-commit is off. Default is on.
                        return True
        except Exception as e:
            print(f"[CLI ERROR] Error during Kafka poll/processing attempt {poll_count}: {e}")
            # Depending on the error, you might want to break or simply log and continue.
            # For now, let it log and continue polling. If it's a persistent consumer error, it will keep logging.
            time.sleep(1) # Brief pause if an error occurs to avoid spamming logs in a tight loop.

    # print(f"[CLI DEBUG] Exited polling loop. Total polls: {poll_count}.") # Uncomment for verbose polling log
    # If the while loop finishes, it means timeout_seconds was reached without a matching response.
    print(f"Timeout: No response received for Request ID {request_id} within {timeout_seconds} seconds.")
    return False

if __name__ == "__main__":
    producer = create_producer()
    # Unique group_id for each CLI instance or None if not needing to resume/share.
    # For this CLI, a unique ID is fine.
    cli_consumer_group_id = f"cli_consumer_{uuid.uuid4()}"
    consumer = create_consumer(FINAL_OUTPUT_TOPIC, group_id=cli_consumer_group_id)
    
    try:
        while True:
            user_input = input("\nEnter your prompt (or 'exit' to quit): ")
            if user_input.lower() == 'exit':
                break
            if not user_input.strip():
                continue

            current_request_id = str(uuid.uuid4())
            send_prompt(producer, USER_PROMPT_TOPIC, current_request_id, user_input)
            
            listen_for_response(consumer, current_request_id)

    except KeyboardInterrupt:
        print("\nCLI exiting.")
    finally:
        producer.close()
        consumer.close()