"""Pluggable message transport with one API in two modes.

InMemoryBroker: synchronous, deterministic — publish() dispatches straight
to matching subscribers in call order. Runs anywhere, used by tests/replay.

RabbitBroker: the same API over RabbitMQ (topic exchange "trade") via pika.
pika is imported lazily so the package works without it installed.

Routing patterns support exact keys and a trailing wildcard, e.g.
"feed.*" matches "feed.livescore" and "feed.markets.1x2"; "#" matches all.
"""
import uuid

from .messages import Message


def pattern_matches(pattern, routing_key):
    """Exact match, "#" catch-all, or trailing-wildcard "prefix.*"."""
    if pattern == routing_key or pattern == "#":
        return True
    if pattern.endswith(".*"):
        return routing_key.startswith(pattern[:-1]) or routing_key == pattern[:-2]
    return False


class Broker:
    """Abstract transport: pub/sub over routing keys + simple RPC."""

    def publish(self, routing_key, message):
        """Send a Message under routing_key to all matching subscribers."""
        raise NotImplementedError

    def subscribe(self, pattern, callback):
        """Register callback(routing_key, message) for keys matching pattern."""
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

    def subscribe(self, pattern, callback):
        self._subs.append((pattern, callback))

    def rpc_serve(self, queue_name, handler):
        self._rpc_handlers[queue_name] = handler

    def rpc_call(self, queue_name, payload, timeout=5.0):
        handler = self._rpc_handlers.get(queue_name)
        if handler is None:
            raise RuntimeError("no RPC handler registered on %r" % queue_name)
        return handler(payload)


class RabbitBroker(Broker):
    """The same API over RabbitMQ (demo-grade, single connection).

    Uses a non-durable topic exchange named "trade". subscribe() binds an
    exclusive queue per pattern; rpc uses the standard exclusive-reply-queue
    + correlation_id pattern. start() blocks in channel.start_consuming(),
    so run it on the consumer side (typically in its own thread or process).
    """

    EXCHANGE = "trade"

    def __init__(self, url="amqp://guest:guest@localhost:5672/%2F"):
        try:
            import pika
        except ImportError:
            raise RuntimeError("RabbitBroker needs the pika package: pip install pika")
        self._pika = pika
        self._conn = pika.BlockingConnection(pika.URLParameters(url))
        self._chan = self._conn.channel()
        self._chan.exchange_declare(exchange=self.EXCHANGE,
                                    exchange_type="topic", durable=False)

    def publish(self, routing_key, message):
        self._chan.basic_publish(exchange=self.EXCHANGE, routing_key=routing_key,
                                 body=message.to_json().encode("utf-8"))

    def subscribe(self, pattern, callback):
        q = self._chan.queue_declare(queue="", exclusive=True).method.queue
        self._chan.queue_bind(exchange=self.EXCHANGE, queue=q, routing_key=pattern)

        def on_message(ch, method, props, body):
            callback(method.routing_key, Message.from_json(body.decode("utf-8")))

        self._chan.basic_consume(queue=q, on_message_callback=on_message,
                                 auto_ack=True)

    def rpc_serve(self, queue_name, handler):
        import json
        self._chan.queue_declare(queue=queue_name, exclusive=False, durable=False)

        def on_request(ch, method, props, body):
            reply = handler(json.loads(body.decode("utf-8")))
            ch.basic_publish(exchange="", routing_key=props.reply_to,
                             properties=self._pika.BasicProperties(
                                 correlation_id=props.correlation_id),
                             body=json.dumps(reply).encode("utf-8"))
            ch.basic_ack(delivery_tag=method.delivery_tag)

        self._chan.basic_consume(queue=queue_name, on_message_callback=on_request)

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
            properties=self._pika.BasicProperties(reply_to=reply_q,
                                                  correlation_id=corr_id),
            body=json.dumps(payload).encode("utf-8"))
        self._conn.process_data_events(time_limit=timeout)
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
