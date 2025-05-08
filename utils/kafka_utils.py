# /full/path/to/project/ollama_multi_agent_kafka/utils/kafka_utils.py
import json
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import NoBrokersAvailable
from config import KAFKA_BROKER
import time

def create_producer():
    try:
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BROKER,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        return producer
    except NoBrokersAvailable:
        print(f"Error: Kafka broker not available at {KAFKA_BROKER}. Is Kafka running?")
        time.sleep(5) # Wait and retry or raise
        raise

def create_consumer(topic, group_id):
    try:
        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=KAFKA_BROKER,
            value_deserializer=lambda v: json.loads(v.decode('utf-8')),
            auto_offset_reset='earliest', # Process messages from the beginning if new group
            group_id=group_id,
            consumer_timeout_ms=1000 # To allow periodic checks for shutdown
        )
        return consumer
    except NoBrokersAvailable:
        print(f"Error: Kafka broker not available at {KAFKA_BROKER}. Is Kafka running?")
        time.sleep(5) # Wait and retry or raise
        raise