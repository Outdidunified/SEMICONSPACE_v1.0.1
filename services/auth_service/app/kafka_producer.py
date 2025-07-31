# app/kafka_producer.py
import os
import json
import asyncio
import logging
from typing import Optional
from aiokafka import AIOKafkaProducer
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()
KAFKA_BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS", "172.235.17.60:9092"
)
producer: Optional[AIOKafkaProducer] = None


async def start_kafka() -> None:
    global producer
    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    # Retry until Kafka is available
    for i in range(10):
        try:
            await producer.start()
            logger.info("✅ Kafka producer started")
            return  # Explicitly return None (successful completion)
        except Exception as e:
            logger.warning(
                f"⏳ Kafka not ready, retrying in 3s ({i+1}/10)... Error: {e}"
            )
            await asyncio.sleep(3)

    # If we reach here, all retries failed
    raise Exception("❌ Kafka did not start after multiple attempts")


async def stop_kafka() -> None:
    if producer:
        await producer.stop()
        logger.info("✅ Kafka producer stopped")
    else:
        logger.info("ℹ️ Kafka producer was not running")


async def send_event(topic: str, data: dict) -> None:
    if producer:
        try:
            await producer.send_and_wait(topic, data)
            logger.info(f"✅ Event sent to topic '{topic}': {data}")
        except Exception as e:
            logger.error(f"❌ Failed to send event to topic '{topic}': {e}")
            raise
    else:
        logger.warning(
            "⚠️ Kafka producer is not initialized. Cannot send event."
        )
        return  # Explicitly return None when producer is not initialized
        return  # Explicitly return None when producer is not initialized
