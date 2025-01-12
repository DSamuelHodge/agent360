"""
Redpanda client service for event streaming.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Callable
from confluent_kafka import Producer, Consumer, KafkaError, KafkaException
from prometheus_client import Counter, Histogram
from opentelemetry import trace
from opentelemetry.trace import Span

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

# Metrics
MESSAGES_PRODUCED = Counter(
    'redpanda_messages_produced_total',
    'Total number of messages produced',
    ['topic']
)
MESSAGES_CONSUMED = Counter(
    'redpanda_messages_consumed_total',
    'Total number of messages consumed',
    ['topic', 'consumer_group']
)
MESSAGE_LATENCY = Histogram(
    'redpanda_message_latency_seconds',
    'Message processing latency in seconds',
    ['topic']
)

class RedpandaClient:
    """Client for interacting with Redpanda event streaming."""
    
    def __init__(
        self,
        bootstrap_servers: str,
        client_id: str,
        producer_config: Optional[Dict[str, Any]] = None,
        consumer_config: Optional[Dict[str, Any]] = None
    ):
        """Initialize Redpanda client.
        
        Args:
            bootstrap_servers: Comma-separated list of broker addresses
            client_id: Unique identifier for this client
            producer_config: Additional producer configuration
            consumer_config: Additional consumer configuration
        """
        self.bootstrap_servers = bootstrap_servers
        self.client_id = client_id
        
        # Producer configuration
        self.producer_config = {
            'bootstrap.servers': bootstrap_servers,
            'client.id': f'{client_id}-producer',
            'acks': 'all',
            'retries': 3,
            'retry.backoff.ms': 1000,
            'compression.type': 'lz4',
            'batch.size': 16384,
            'linger.ms': 10,
        }
        if producer_config:
            self.producer_config.update(producer_config)
        
        # Consumer configuration
        self.consumer_config = {
            'bootstrap.servers': bootstrap_servers,
            'client.id': f'{client_id}-consumer',
            'group.id': client_id,
            'auto.offset.reset': 'earliest',
            'enable.auto.commit': False,
            'max.poll.interval.ms': 300000,
            'session.timeout.ms': 30000,
        }
        if consumer_config:
            self.consumer_config.update(consumer_config)
        
        self.producer = None
        self.consumer = None
    
    def _delivery_report(self, err: Optional[KafkaError], msg: Any) -> None:
        """Delivery report callback for producer.
        
        Args:
            err: Error that occurred, if any
            msg: Message that was produced
        """
        if err is not None:
            logger.error(f'Message delivery failed: {err}')
        else:
            topic = msg.topic()
            MESSAGES_PRODUCED.labels(topic=topic).inc()
    
    async def produce(
        self,
        topic: str,
        value: Dict[str, Any],
        key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> None:
        """Produce a message to a topic.
        
        Args:
            topic: Topic to produce to
            value: Message value
            key: Optional message key
            headers: Optional message headers
        """
        with tracer.start_as_current_span('redpanda.produce') as span:
            try:
                if not self.producer:
                    self.producer = Producer(self.producer_config)
                
                # Add tracing context to headers
                if headers is None:
                    headers = {}
                headers['trace_id'] = str(span.get_span_context().trace_id)
                headers['span_id'] = str(span.get_span_context().span_id)
                
                # Produce message
                self.producer.produce(
                    topic=topic,
                    key=key.encode() if key else None,
                    value=json.dumps(value).encode(),
                    headers=[(k, v.encode()) for k, v in headers.items()],
                    callback=self._delivery_report
                )
                self.producer.poll(0)  # Trigger delivery reports
                
                span.set_attribute('messaging.system', 'redpanda')
                span.set_attribute('messaging.destination', topic)
                span.set_attribute('messaging.destination_kind', 'topic')
                
            except Exception as e:
                logger.error(f'Error producing message: {e}')
                span.record_exception(e)
                raise
    
    async def consume(
        self,
        topics: List[str],
        handler: Callable[[str, Dict[str, Any], Optional[Dict[str, str]]], None],
        group_id: Optional[str] = None,
        auto_commit: bool = False
    ) -> None:
        """Consume messages from topics.
        
        Args:
            topics: List of topics to consume from
            handler: Callback function to handle messages
            group_id: Optional consumer group ID
            auto_commit: Whether to auto-commit offsets
        """
        if group_id:
            self.consumer_config['group.id'] = group_id
        self.consumer_config['enable.auto.commit'] = auto_commit
        
        try:
            if not self.consumer:
                self.consumer = Consumer(self.consumer_config)
            
            self.consumer.subscribe(topics)
            
            while True:
                msg = self.consumer.poll(1.0)
                
                if msg is None:
                    continue
                
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        logger.error(f'Consumer error: {msg.error()}')
                        break
                
                with MESSAGE_LATENCY.labels(topic=msg.topic()).time():
                    with tracer.start_as_current_span('redpanda.consume') as span:
                        try:
                            # Extract message data
                            value = json.loads(msg.value().decode())
                            headers = {
                                k: v.decode()
                                for k, v in msg.headers() if v is not None
                            } if msg.headers() else None
                            
                            # Extract tracing context from headers
                            if headers and 'trace_id' in headers:
                                span.set_attribute('trace_id', headers['trace_id'])
                            
                            # Process message
                            await handler(msg.topic(), value, headers)
                            
                            # Update metrics
                            MESSAGES_CONSUMED.labels(
                                topic=msg.topic(),
                                consumer_group=group_id or self.client_id
                            ).inc()
                            
                            if not auto_commit:
                                self.consumer.commit(msg)
                            
                        except Exception as e:
                            logger.error(f'Error processing message: {e}')
                            span.record_exception(e)
                            raise
                
        except KeyboardInterrupt:
            logger.info('Shutting down consumer...')
        finally:
            if self.consumer:
                self.consumer.close()
    
    def close(self) -> None:
        """Close producer and consumer connections."""
        if self.producer:
            self.producer.flush()
            self.producer.close()
        if self.consumer:
            self.consumer.close()
