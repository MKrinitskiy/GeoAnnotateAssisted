import threading
import logging
from queue import Queue
from async_rabbitmq_publisher import RabbitMQPublisher

def start_message_publisher_thread(departing_reports_queue, threading_lock):
    """Function to start a thread for publishing messages to RabbitMQ."""
    logger = logging.getLogger("MessagePublisher")

    publisher = RabbitMQPublisher(departing_reports_queue, threading_lock, logger)

    publisher_thread = threading.Thread(target=publisher.run)
    publisher_thread.start()

    return publisher_thread
