import threading
import logging
from app import arriving_messages_queue
from async_rabbitmq_consumer import ReconnectingRabbitMQConsumer

def start_message_consumer_thread(threading_lock):
    """Function to start a thread for consuming messages from RabbitMQ."""
    threading_lock = threading.Lock()
    logger = logging.getLogger("MessageConsumer")

    consumer = ReconnectingRabbitMQConsumer(arriving_messages_queue, threading_lock, logger)

    consumer_thread = threading.Thread(target=consumer.run)
    consumer_thread.start()

    return consumer_thread
