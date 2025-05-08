# /full/path/to/project/ollama_multi_agent_kafka/run_agents.py
import multiprocessing
import time
from agents.master_agent import main as master_main
from agents.research_agent import main as research_main
from agents.writing_agent import main as writing_main

def run_agent_process(agent_name, agent_main_func):
    print(f"Starting {agent_name} agent...")
    try:
        agent_main_func()
    except KeyboardInterrupt:
        print(f"{agent_name} agent stopping due to KeyboardInterrupt.")
    except Exception as e:
        print(f"{agent_name} agent crashed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print(f"{agent_name} agent stopped.")

if __name__ == "__main__":
    agent_runners = {
        "Master": master_main,
        "Research": research_main,
        "Writing": writing_main,
    }

    processes = []
    for name, main_func in agent_runners.items():
        process = multiprocessing.Process(target=run_agent_process, args=(name, main_func))
        processes.append(process)
        process.start()
        time.sleep(1) # Stagger agent starts slightly

    print("All agents started. Press Ctrl+C in this terminal to attempt graceful shutdown.")

    try:
        for process in processes:
            process.join() # Wait for all processes to complete
    except KeyboardInterrupt:
        print("\nMain process received Ctrl+C. Terminating agent processes...")
        for process in processes:
            if process.is_alive():
                process.terminate() # Force terminate if still running
                process.join(timeout=5) # Wait for termination
    finally:
        print("All agent processes have been handled.")