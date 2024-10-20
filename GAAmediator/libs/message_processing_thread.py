import threading
import logging
from queue import Queue, Empty

def start_message_processing_thread(arriving_messages_queue, departing_reports_queue):
    """Function to start a thread for processing messages from the incoming queue and placing them into the outgoing queue."""
    def process_messages():
        logger = logging.getLogger("MessageProcessor")
        while True:
            try:
                message = arriving_messages_queue.get(timeout=1)  # Wait for a message
                logger.info(f"Processing message: {message}")
                # Simulate processing
                processed_message = message  # Replace with actual processing logic
                departing_reports_queue.put(processed_message)
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing message: {e}")

    processing_thread = threading.Thread(target=process_messages)
    processing_thread.start()

    return processing_thread
