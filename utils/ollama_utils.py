# /full/path/to/project/ollama_multi_agent_kafka/utils/ollama_utils.py
import ollama
import json
import os
from config import OLLAMA_BASE_URL, OLLAMA_MODEL

# Initialize client once. The 'ollama' library uses OLLAMA_HOST env var by default.
# Explicitly setting it ensures we use the config.
try:
    ollama_client = ollama.Client(host=OLLAMA_BASE_URL)
    # Test connection by listing models (optional)
    # ollama_client.list()
except Exception as e:
    print(f"Failed to initialize Ollama client with host {OLLAMA_BASE_URL}: {e}")
    print("Ensure Ollama service is running and accessible, and OLLAMA_BASE_URL in config.py is correct.")
    ollama_client = None # Indicate failure

def get_ollama_response(prompt_text, expect_json=False, model_name=OLLAMA_MODEL):
    if not ollama_client:
        raise ConnectionError("Ollama client not initialized. Check Ollama service and configuration.")
    try:
        response = ollama_client.generate(
            model=model_name,
            prompt=prompt_text,
            stream=False,
            format="json" if expect_json else ""
        )
        content = response['response']

        if expect_json:
            # format="json" should provide valid JSON, but clean up potential markdown
            cleaned_content = content.strip().removeprefix("```json").removesuffix("```").strip()
            return json.loads(cleaned_content)
        return content.strip()
    except json.JSONDecodeError as je:
        print(f"JSONDecodeError: Failed to parse LLM JSON output. Raw content: '{content}'. Error: {je}")
        raise
    except Exception as e:
        print(f"Error communicating with Ollama or processing response: {e}")
        raise