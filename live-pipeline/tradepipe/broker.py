"""Pluggable message transport with one API in two modes.

InMemoryBroker: synchronous, deterministic — publish() dispatches straight
to matching subscribers in call order. Runs anywhere, used by tests/replay.

RabbitBroker: the same API over RabbitMQ (topic exchange "trade") via pika.
pika is imported lazily so the package works without it installed. Durable
by default: persistent messages, durable exchange and queues, publisher
confirms and manual acknowledgement, so a consumer that dies mid-message
redelivers it rather than dropping it.

Routing follows AMQP topic-exchange semantics exactly, because a pattern
that behaves one way in tests and another way on the wire is worse than no
abstraction at all: keys are dot-separated words, "*" matches exactly ONE
word, and "#" matches zero or more. So "feed.*" matches "feed.123" but not
"feed.123.markets"; "feed.#" matches both.
"""
import uuid

from .messages import Message

DEFAULT_URL = "amqp://guest:guest@localhost:5672/%2F"


def pattern_matches(pattern, routing_key):
    """AMQP topic match: "*" is exactly one word, "#" is zero or more."""
    return _match(pattern.split("."), routing_key.split("."))


def _match(pat, key):
    """Recursive word-by-word match of a split pattern against a split key."""
    if not pat:
        return not key
    head = pat[0]
    if head == "#":
        # "#" absorbs any number of words, including none: try each split.
        return any(_match(pat[1:], key[i:]) for i in range(len(key) + 1))
    if not key:
        return False
    if head == "*" or head == key[0]:
        return _match(pat[1:], key[1:])
    return False


class Broker:
    """Abstract transport: pub/sub over routing keys + simple RPC."""

    def publish(self, routing_key, message):
        """Send a Message under routing_key to all matching subscribers."""
        raise NotImplementedError

    def subscribe(self, pattern, callback, queue=None):
        """Register callback(routing_key, message) for keys matching pattern.

        `queue` names a durable, shared queue (work-queue semantics: each
        message goes to one of the consumers on that name, and it survives
        a broker restart). Omit it for a private, transient subscription."""
        raise NotImplementedError

    def rpc_serve(self, queue_name, handler):
        """Serve requests on queue_name; handler(payload dict) -> reply dict."""
        raise NotImplementedError

    def rpc_call(self, queue_name, payload, timeout=5.0):
        """Send payload dict to queue_name's handler, return its reply dict."""
        raise NotImplementedError

    def start(self):
        """Begin consuming (no-op for the in-memory broker)."""
        pass

    def close(self):
        pass


class InMemoryBroker(Broker):
    """Synchronous in-process broker: callbacks fire in publish order."""

    def __init__(self):
        self._subs = []                          # (pattern, callback)
        self._rpc_handlers = {}                  # queue_name -> handler

    def publish(self, routing_key, message):
        for pattern, callback in self._subs:
            if pattern_matches(pattern, routing_key):
                callback(routing_key, message)

    def subscribe(self, pattern, callback, queue=None):
        self._subs.append((pattern, callback))   # `queue` is a no-op in process

    def rpc_serve(self, queue_name, handler):
        self._rpc_handlers[queue_name] = handler

    def rpc_call(self, queue_name, payload, timeout=5.0):
        handler = self._rpc_handlers.get(queue_name)
        if handler is None:
            raise RuntimeError("no RPC handler registered on %r" % queue_name)
        return handler(payload)


class RabbitBroker(Broker):
    """The same API over RabbitMQ (topic exchange "trade").

    Durable by default, which is the difference between a demo and a feed
    you would actually run:

      * the exchange and any named queue survive a broker restart, and
        messages are published persistent (delivery_mode 2);
      * publisher confirms mean publish() raises instead of silently
        dropping when the broker never took the message;
      * consumers acknowledge MANUALLY, after their callback returns, so a
        consumer that crashes mid-message gets it redelivered rather than
        losing it. A callback that raises nacks WITHOUT requeue, so one
        poison message cannot spin forever.

    Pass durable=False for the old fire-and-forget behaviour. start()
    blocks in channel.start_consuming(), so run it on the consumer side
    (typically in its own thread or process).
    """

    EXCHANGE = "trade"

    def __init__(self, url=DEFAULT_URL, durable=True, prefetch=50):
        try:
            import pika
        except ImportError:
            raise RuntimeError("RabbitBroker needs the pika package: pip install pika")
        self._pika = pika
        self.durable = durable
        self._conn = pika.BlockingConnection(pika.URLParameters(url))
        self._chan = self._conn.channel()
        self._chan.exchange_declare(exchange=self.EXCHANGE,
                                    exchange_type="topic", durable=durable)
        self._chan.basic_qos(prefetch_count=prefetch)
        if durable:
            self._chan.confirm_delivery()        # publish() raises on failure

    def _props(self, message=None, **kw):
        return self._pika.BasicProperties(
            delivery_mode=2 if self.durable else 1,
            message_id=message.msg_guid if message else None, **kw)

    def publish(self, routing_key, message):
        self._chan.basic_publish(exchange=self.EXCHANGE, routing_key=routing_key,
                                 body=message.to_json().encode("utf-8"),
                                 properties=self._props(message))

    def subscribe(self, pattern, callback, queue=None):
        """Bind a queue to `pattern`. Named queues are durable and shared;
        anonymous ones are exclusive and die with the connection."""
        if queue:
            q = self._chan.queue_declare(queue=queue, durable=self.durable).method.queue
        else:
            q = self._chan.queue_declare(queue="", exclusive=True).method.queue
        self._chan.queue_bind(exchange=self.EXCHANGE, queue=q, routing_key=pattern)

        def on_message(ch, method, props, body):
            try:
                callback(method.routing_key, Message.from_json(body.decode("utf-8")))
            except Exception:
                # Do not requeue: a message this consumer cannot parse will
                # fail the same way forever. Drop it and keep the feed moving.
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                raise
            ch.basic_ack(delivery_tag=method.delivery_tag)

        self._chan.basic_consume(queue=q, on_message_callback=on_message,
                                 auto_ack=False)
        return q

    def rpc_serve(self, queue_name, handler):
        import json
        self._chan.queue_declare(queue=queue_name, durable=self.durable)

        def on_request(ch, method, props, body):
            reply = handler(json.loads(body.decode("utf-8")))
            ch.basic_publish(exchange="", routing_key=props.reply_to,
                             properties=self._props(
                                 correlation_id=props.correlation_id),
                             body=json.dumps(reply).encode("utf-8"))
            ch.basic_ack(delivery_tag=method.delivery_tag)

        self._chan.basic_consume(queue=queue_name, on_message_callback=on_request,
                                 auto_ack=False)

    def rpc_call(self, queue_name, payload, timeout=5.0):
        import json
        reply_q = self._chan.queue_declare(queue="", exclusive=True).method.queue
        corr_id = str(uuid.uuid4())
        response = {}

        def on_reply(ch, method, props, body):
            if props.correlation_id == corr_id:
                response["value"] = json.loads(body.decode("utf-8"))

        tag = self._chan.basic_consume(queue=reply_q, on_message_callback=on_reply,
                                       auto_ack=True)
        self._chan.basic_publish(
            exchange="", routing_key=queue_name,
            properties=self._props(reply_to=reply_q, correlation_id=corr_id),
            body=json.dumps(payload).encode("utf-8"))
        deadline = timeout
        while "value" not in response and deadline > 0:
            step = min(0.25, deadline)
            self._conn.process_data_events(time_limit=step)
            deadline -= step
        self._chan.basic_cancel(tag)
        if "value" not in response:
            raise TimeoutError("no RPC reply from %r within %ss" % (queue_name, timeout))
        return response["value"]

    def start(self):
        self._chan.start_consuming()             # blocks; run in a thread if needed

    def close(self):
        try:
            self._chan.stop_consuming()
        except Exception:
            pass
        self._conn.close()


def get_broker(name, **kw):
    """Factory: "memory" -> InMemoryBroker, "rabbit" -> RabbitBroker."""
    if name == "memory":
        return InMemoryBroker(**kw)
    if name == "rabbit":
        return RabbitBroker(**kw)
    raise ValueError("unknown broker %r (use 'memory' or 'rabbit')" % name)
