from confluent_kafka import Consumer, Message

class CommitManager:
    def __init__(self, consumer: Consumer) -> None:
        self._consumer = consumer

    def commit_sync(self, message: Message) -> None:
        self._consumer.commit(message=message, asynchronous=False)

    def commit_async(self, message: Message) -> None:
        self._consumer.commit(message=message, asynchronous=True)
