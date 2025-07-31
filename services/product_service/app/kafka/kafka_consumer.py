import os
import json
import logging
import asyncio
from typing import Dict, Any, cast
from aiokafka import AIOKafkaConsumer
from dotenv import load_dotenv

from app.update.update_quantity import reduce_product_stock

load_dotenv()
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

KAFKA_BOOTSTRAP_SERVERS = cast(str, os.getenv("KAFKA_BOOTSTRAP_SERVERS"))
KAFKA_TOPIC = "payment.success"
KAFKA_CONSUMER_GROUP = "product_service_group"

if not KAFKA_BOOTSTRAP_SERVERS:
    raise RuntimeError("Kafka environment variables are not set properly.")


def safe_json_deserializer(value: bytes) -> Dict[str, Any] | None:
    try:
        return json.loads(value.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.error(f"❌ Failed to deserialize Kafka message: {e}")
        return None


async def start_consumer() -> None:
    consumer = AIOKafkaConsumer(
    KAFKA_TOPIC,
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    group_id=KAFKA_CONSUMER_GROUP,
    client_id="product-service-consumer",
    value_deserializer=safe_json_deserializer,
    enable_auto_commit=True,
    auto_offset_reset="latest",
    session_timeout_ms=30000,
    heartbeat_interval_ms=10000,
    request_timeout_ms=40000,
    max_poll_interval_ms=600000,
)

    # 🔁 Retry Kafka consumer until ready
    while True:
        try:
            await consumer.start()
            logger.info(f"✅ Kafka consumer started for topic: {KAFKA_TOPIC}")
            break
        except Exception as e:
            logger.warning(f"⏳ Kafka not ready, retrying in 3s: {e}")
            await asyncio.sleep(3)

    try:
        async for msg in consumer:
            event = msg.value
            if event is None:
                logger.warning("⚠️ Received None event from Kafka, skipping...")
                continue

            logger.info(f"📥 Received Kafka message: {event}")

            if not isinstance(event, dict):
                logger.warning(f"⚠️ Invalid event format: {type(event)}")
                continue

            order_id = event.get("orderId")
            user_id = event.get("userId")
            logger.info(f"🧾 Processing order {order_id} for user {user_id}")

            items = event.get("items")
            if not items or not isinstance(items, list):
                logger.warning("⚠️ No valid items found in event")
                continue

            for item in items:
                product_event = {
                    "product_id": item.get("productId"),
                    "quantity": item.get("qty", 1),
                }
                await reduce_product_stock(product_event)

    except asyncio.CancelledError:
        logger.info("🛑 Kafka consumer cancelled")
    finally:
        await consumer.stop()
        logger.info("👋 Kafka consumer stopped")
