# /c:\workspace\ai-agent\multi-agent-event-communication\agents\concurrent_master_agent.py
import json
import time
import uuid
from collections import defaultdict

from utils.kafka_utils import create_producer, create_consumer
from utils.ollama_utils import get_ollama_response
from config import (
    USER_PROMPT_TOPIC, AGENT_TASKS_PREFIX, AGENT_RESULTS_TOPIC,
    FINAL_OUTPUT_TOPIC, AGENT_RESEARCHER, AGENT_WRITER
)

# In-memory store for active requests and their states
active_requests = {}

def get_task_plan(user_prompt, request_id):
    print(f"[PARALLEL_MASTER_AGENT] Request {request_id}: Generating task plan for: {user_prompt}")
    prompt = f"""You are a master planner agent. Your goal is to break down a user's request into a series of tasks that can be executed by specialized agents.
The available specialized agents are: '{AGENT_RESEARCHER}' and '{AGENT_WRITER}'.
- A '{AGENT_RESEARCHER}' agent finds information.
- A '{AGENT_WRITER}' agent composes text based on provided information.

User Request: "{user_prompt}"

Based on this request, define a plan as a JSON list of tasks. Each task object in the list should have:
- "task_id": A unique identifier for the task (e.g., "task_1", "task_2").
- "agent_type": The type of agent to perform this task (either "{AGENT_RESEARCHER}" or "{AGENT_WRITER}").
- "description": A clear, concise instruction for the specialized agent.
- "dependencies": A list of "task_id"s that must be completed before this task can start. An empty list means no dependencies.
- "inputs_from_dependencies": A list of "task_id"s whose results should be fed as input to this task. This is often the same as dependencies.

Important considerations:
- A '{AGENT_WRITER}' agent usually depends on a '{AGENT_RESEARCHER}' agent's output.
- Ensure the 'description' for each task is self-contained and actionable for the designated agent.
- If the request is simple and can be handled by one agent, create a single task.

Output ONLY the JSON list of tasks. Do not include any other explanatory text.
Example:
[
  {{"task_id": "task_1", "agent_type": "{AGENT_RESEARCHER}", "description": "Research topic X", "dependencies": [], "inputs_from_dependencies": []}},
  {{"task_id": "task_2", "agent_type": "{AGENT_WRITER}", "description": "Write a summary about topic X using research findings.", "dependencies": ["task_1"], "inputs_from_dependencies": ["task_1"]}}
]
"""
    try:
        plan = get_ollama_response(prompt, expect_json=True)

        # Check if the LLM wrapped the list in an object (e.g., {"tasks": [...]})
        if isinstance(plan, dict) and "tasks" in plan and isinstance(plan["tasks"], list):
            plan = plan["tasks"]

        if not isinstance(plan, list):
            print(f"[PARALLEL_MASTER_AGENT] Request {request_id}: Plan generation returned non-list: {plan}")
            raise ValueError("LLM did not return a list for the plan.")
        # Validate plan structure (basic)
        for i, task in enumerate(plan):
            if not all(k in task for k in ["task_id", "agent_type", "description", "dependencies", "inputs_from_dependencies"]):
                raise ValueError(f"Task {i} in plan is malformed: {task}")
            task["task_id"] = f"{request_id}_{task['task_id']}" # Ensure task_ids are unique across requests
            # Update dependencies to use the new prefixed task_ids
            task["dependencies"] = [f"{request_id}_{dep_id}" for dep_id in task["dependencies"]]
            task["inputs_from_dependencies"] = [f"{request_id}_{dep_id}" for dep_id in task["inputs_from_dependencies"]]

        print(f"[PARALLEL_MASTER_AGENT] Request {request_id}: Plan generated: {plan}")
        return plan
    except Exception as e:
        print(f"[PARALLEL_MASTER_AGENT] Request {request_id}: Error generating task plan: {e}")
        return None

def dispatch_tasks(producer, request_id):
    if request_id not in active_requests:
        return

    req_data = active_requests[request_id]
    for task_def in req_data["plan"]:
        task_id = task_def["task_id"]
        if req_data["tasks_status"].get(task_id) == "pending":
            # Check dependencies
            dependencies_met = True
            for dep_id in task_def["dependencies"]:
                if req_data["tasks_status"].get(dep_id) != "completed":
                    dependencies_met = False
                    break
            
            if dependencies_met:
                print(f"[PARALLEL_MASTER_AGENT] Request {request_id}: Dispatching task {task_id} to {task_def['agent_type']}")
                
                input_data_for_task = {}
                for dep_id in task_def.get("inputs_from_dependencies", []):
                    dep_task_name = dep_id.split('_',1)[1] if '_' in dep_id else dep_id # Get original task name for context key
                    input_data_for_task[f"result_from_{dep_task_name}"] = req_data["tasks_results"].get(dep_id)

                task_payload = {
                    "request_id": request_id,
                    "task_id": task_id,
                    "agent_type": task_def["agent_type"],
                    "description": task_def["description"],
                    "input_data": input_data_for_task
                }
                topic = f"{AGENT_TASKS_PREFIX}{task_def['agent_type']}"
                producer.send(topic, value=task_payload)
                req_data["tasks_status"][task_id] = "dispatched"
    producer.flush()

def synthesize_final_response(request_id):
    req_data = active_requests[request_id]
    formatted_results = []
    for task_def in req_data["plan"]:
        task_id = task_def["task_id"]
        result = req_data["tasks_results"].get(task_id, "No result")
        formatted_results.append(f"Task '{task_def['description']}' ({task_def['agent_type']}) result:\n{result}")
    
    results_str = "\n\n".join(formatted_results)
    prompt = f"""You are a master agent responsible for synthesizing a final response to the user.
Original User Request: "{req_data['original_prompt']}"

The following information was gathered and processed by specialized agents:
{results_str}

Based on the original request and the gathered information, provide a comprehensive and helpful response to the user.
If a task failed, mention it and explain how it affects the final answer.
"""
    try:
        final_response = get_ollama_response(prompt)
        print(f"[PARALLEL_MASTER_AGENT] Request {request_id}: Final response synthesized.")
        return final_response
    except Exception as e:
        print(f"[PARALLEL_MASTER_AGENT] Request {request_id}: Error synthesizing final response: {e}")
        return f"Error: Could not synthesize final response due to: {e}"

def main():
    print("[PARALLEL_MASTER_AGENT] Starting...")
    producer = create_producer()
    user_prompt_consumer = create_consumer(USER_PROMPT_TOPIC, group_id="parallel_master_agent_user_prompts") # Unique group_id
    results_consumer = create_consumer(AGENT_RESULTS_TOPIC, group_id="parallel_master_agent_results")       # Unique group_id
    print(f"[PARALLEL_MASTER_AGENT] Listening for user prompts on {USER_PROMPT_TOPIC} and results on {AGENT_RESULTS_TOPIC}")

    try:
        while True:
            # Poll for user prompts with a short timeout
            user_prompt_records = user_prompt_consumer.poll(timeout_ms=100) # e.g., 100ms
            if user_prompt_records:
                for tp, messages in user_prompt_records.items():
                    for message_obj in messages:
                        data = message_obj.value # Already deserialized
                        request_id = data["request_id"]
                        prompt = data["prompt"]
                        print(f"[PARALLEL_MASTER_AGENT] Received new user prompt (Request ID: {request_id}): {prompt}")
                        
                        plan = get_task_plan(prompt, request_id)
                        if plan:
                            active_requests[request_id] = {
                                "original_prompt": prompt,
                                "plan": plan,
                                "tasks_status": {task["task_id"]: "pending" for task in plan},
                                "tasks_results": {}
                            }
                            dispatch_tasks(producer, request_id)
                        else:
                            # Failed to get a plan, inform user
                            error_response = {"request_id": request_id, "final_response": f"Failed to process your request: Could not generate a task plan for '{prompt}'."}
                            producer.send(FINAL_OUTPUT_TOPIC, value=error_response)
                            producer.flush()

            # Poll for agent results with a short timeout
            agent_result_records = results_consumer.poll(timeout_ms=100) # e.g., 100ms
            if agent_result_records:
                for tp, messages in agent_result_records.items():
                    for message_obj in messages:
                        result_data = message_obj.value # Already deserialized
                        request_id = result_data["request_id"]
                        task_id = result_data["task_id"]

                        if request_id in active_requests:
                            req_data = active_requests[request_id]
                            print(f"[PARALLEL_MASTER_AGENT] Request {request_id}: Received result for task {task_id}, status: {result_data['status']}")
                            
                            req_data["tasks_status"][task_id] = result_data["status"]
                            if result_data["status"] == "completed":
                                req_data["tasks_results"][task_id] = result_data["result"]
                            else: # Task failed
                                req_data["tasks_results"][task_id] = f"Error: {result_data.get('error_message', 'Unknown error')}"

                            # Check if all tasks for this request are done
                            all_done = all(status in ["completed", "failed"] for status in req_data["tasks_status"].values())
                            
                            if all_done:
                                print(f"[PARALLEL_MASTER_AGENT] Request {request_id}: All tasks completed or failed. Synthesizing final response.")
                                final_response_content = synthesize_final_response(request_id)
                                producer.send(FINAL_OUTPUT_TOPIC, value={"request_id": request_id, "final_response": final_response_content})
                                if request_id in active_requests: 
                                    del active_requests[request_id] # Clean up
                            else:
                                dispatch_tasks(producer, request_id) # Dispatch any newly unblocked tasks
            
            # time.sleep(0.01) # Optional: if CPU usage is a concern with very frequent polling

    except KeyboardInterrupt:
        print("[PARALLEL_MASTER_AGENT] Shutting down...")
    finally:
        if user_prompt_consumer: user_prompt_consumer.close()
        if results_consumer: results_consumer.close()
        if producer: producer.close()

if __name__ == "__main__":
    main()