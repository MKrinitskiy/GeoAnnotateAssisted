import asyncio
from GAAmediator.libs.message_consumer_thread import start_message_consumer_thread

from GAAmediator.libs.message_publisher_thread import start_message_publisher_thread
from queue import Queue

arriving_messages_queue = Queue()

departing_reports_queue = Queue()

async def main():
    consumer_thread = start_message_consumer_thread()
    publisher_thread = start_message_publisher_thread(departing_reports_queue)
    while True:
        try:
            # Placeholder for the main logic
            await asyncio.sleep(1)  # Simulate async work
        except KeyboardInterrupt:
            print("Keyboard interruption received. Exiting...")
            break

if __name__ == "__main__":
    asyncio.run(main())
