import pika
import threading

def process_incoming_messages():
    """Function to process incoming messages from RabbitMQ."""
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()

    channel.queue_declare(queue='incoming')

    def callback(ch, method, properties, body):
        print(f"Received {body}")

    channel.basic_consume(queue='incoming', on_message_callback=callback, auto_ack=True)

    print('Waiting for messages. To exit press CTRL+C')
    channel.start_consuming()

# Example of starting this function in a separate thread
if __name__ == "__main__":
    thread = threading.Thread(target=process_incoming_messages)
    thread.start()
