import asyncio
from GAAmediator.libs.message_consumer_thread import start_message_consumer_thread

from GAAmediator.libs.message_publisher_thread import start_message_publisher_thread
from GAAmediator.libs.message_processing_thread import start_message_processing_thread
from queue import Queue

arriving_messages_queue = Queue()

departing_reports_queue = Queue()

threading_lock_consumer = threading.Lock()
threading_lock_publisher = threading.Lock()

async def main():
    consumer_thread = start_message_consumer_thread(threading_lock_consumer)
    publisher_thread = start_message_publisher_thread(departing_reports_queue, threading_lock_publisher)
    processing_thread = start_message_processing_thread(arriving_messages_queue, departing_reports_queue)
    
    while True:
        try:
            # Placeholder for the main logic
            await asyncio.sleep(1)  # Simulate async work
        except KeyboardInterrupt:
            print("Keyboard interruption received. Exiting...")
            break

if __name__ == "__main__":
    asyncio.run(main())
