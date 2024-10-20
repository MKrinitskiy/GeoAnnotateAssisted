import asyncio
from GAAmediator.libs.message_consumer_thread import start_message_consumer_thread

from queue import Queue

arriving_messages_queue = Queue()

async def main():
    consumer_thread = start_message_consumer_thread()
    
    while True:
        try:
            # Placeholder for the main logic
            await asyncio.sleep(1)  # Simulate async work
        except KeyboardInterrupt:
            print("Keyboard interruption received. Exiting...")
            break

if __name__ == "__main__":
    asyncio.run(main())
