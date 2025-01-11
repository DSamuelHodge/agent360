# Agent360 Monitoring Guide

## Overview
This guide outlines the monitoring strategy and implementation for Agent360.

## Table of Contents
1. [Metrics Collection](#metrics-collection)
2. [Alert Configuration](#alert-configuration)
3. [Dashboard Setup](#dashboard-setup)
4. [Log Management](#log-management)
5. [Tracing](#tracing)
6. [Reporting](#reporting)

## Metrics Collection

### Application Metrics
```python
# metrics/application.py
from prometheus_client import Counter, Histogram, Gauge

# Request metrics
request_counter = Counter(
    'agent360_requests_total',
    'Total requests processed',
    ['endpoint', 'method', 'status']
)

request_latency = Histogram(
    'agent360_request_duration_seconds',
    'Request duration in seconds',
    ['endpoint'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0]
)

# Resource metrics
memory_usage = Gauge(
    'agent360_memory_usage_bytes',
    'Memory usage in bytes'
)

cpu_usage = Gauge(
    'agent360_cpu_usage_percent',
    'CPU usage percentage'
)
```

### System Metrics
```yaml
# prometheus/node-exporter.yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: node-exporter
spec:
  selector:
    matchLabels:
      app: node-exporter
  template:
    spec:
      containers:
      - name: node-exporter
        image: prom/node-exporter
        ports:
        - containerPort: 9100
        volumeMounts:
        - name: proc
          mountPath: /host/proc
        - name: sys
          mountPath: /host/sys
```

### Database Metrics
```yaml
# prometheus/database-metrics.yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: database-monitor
spec:
  selector:
    matchLabels:
      app: cassandra
  endpoints:
  - port: metrics
    interval: 15s
```

## Alert Configuration

### Alert Rules
```yaml
# prometheus/alert-rules.yaml
groups:
- name: agent360
  rules:
  - alert: HighErrorRate
    expr: |
      sum(rate(agent360_requests_total{status=~"5.."}[5m])) 
      / 
      sum(rate(agent360_requests_total[5m])) > 0.1
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: High error rate detected
      description: Error rate is above 10% for 5 minutes

  - alert: HighLatency
    expr: |
      histogram_quantile(0.95, 
        sum(rate(agent360_request_duration_seconds_bucket[5m])) 
        by (le, endpoint)
      ) > 2
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: High latency detected
      description: 95th percentile latency is above 2 seconds

  - alert: HighMemoryUsage
    expr: |
      container_memory_usage_bytes{container="agent360"}
      /
      container_spec_memory_limit_bytes{container="agent360"}
      > 0.85
    for: 15m
    labels:
      severity: warning
    annotations:
      summary: High memory usage
      description: Memory usage above 85% for 15 minutes
```

### Alert Routing
```yaml
# alertmanager/config.yaml
route:
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: 'team-agent360'
  routes:
  - match:
      severity: critical
    receiver: 'team-agent360-critical'
    repeat_interval: 1h

receivers:
- name: 'team-agent360'
  slack_configs:
  - channel: '#agent360-alerts'
    send_resolved: true

- name: 'team-agent360-critical'
  slack_configs:
  - channel: '#agent360-critical'
    send_resolved: true
  pagerduty_configs:
  - service_key: '<pagerduty-key>'
```

## Dashboard Setup

### Grafana Dashboard
```json
{
  "dashboard": {
    "title": "Agent360 Overview",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "sum(rate(agent360_requests_total[5m])) by (endpoint)",
            "legendFormat": "{{endpoint}}"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "sum(rate(agent360_requests_total{status=~\"5..\"}[5m])) / sum(rate(agent360_requests_total[5m]))",
            "legendFormat": "Error Rate"
          }
        ]
      },
      {
        "title": "Latency",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, sum(rate(agent360_request_duration_seconds_bucket[5m])) by (le, endpoint))",
            "legendFormat": "{{endpoint}} p95"
          }
        ]
      },
      {
        "title": "Resource Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "agent360_memory_usage_bytes",
            "legendFormat": "Memory"
          },
          {
            "expr": "agent360_cpu_usage_percent",
            "legendFormat": "CPU"
          }
        ]
      }
    ]
  }
}
```

## Log Management

### Log Configuration
```yaml
# fluentd/config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluentd-config
data:
  fluent.conf: |
    <source>
      @type tail
      path /var/log/containers/*.log
      pos_file /var/log/fluentd-containers.log.pos
      tag kubernetes.*
      read_from_head true
      <parse>
        @type json
        time_key time
        time_format %Y-%m-%dT%H:%M:%S.%NZ
      </parse>
    </source>

    <filter kubernetes.**>
      @type kubernetes_metadata
      @id filter_kube_metadata
    </filter>

    <match kubernetes.var.log.containers.**agent360**.log>
      @type elasticsearch
      host elasticsearch-logging
      port 9200
      logstash_format true
      logstash_prefix agent360
      <buffer>
        @type file
        path /var/log/fluentd-buffers/kubernetes.system.buffer
        flush_mode interval
        retry_type exponential_backoff
        flush_interval 5s
        retry_forever false
        retry_max_interval 30
        chunk_limit_size 2M
        queue_limit_length 8
        overflow_action block
      </buffer>
    </match>
```

### Log Analysis
```python
# logging/analyzer.py
class LogAnalyzer:
    def analyze_logs(self, timeframe: str):
        # Query Elasticsearch
        logs = self.query_elasticsearch(timeframe)
        
        # Analyze patterns
        patterns = self.analyze_patterns(logs)
        
        # Generate insights
        return self.generate_insights(patterns)
    
    def analyze_patterns(self, logs):
        from collections import Counter
        
        # Count error types
        error_types = Counter(
            log['error_type']
            for log in logs
            if log.get('level') == 'ERROR'
        )
        
        # Analyze request patterns
        request_patterns = Counter(
            log['endpoint']
            for log in logs
            if log.get('type') == 'request'
        )
        
        return {
            'error_types': error_types,
            'request_patterns': request_patterns
        }
```

## Tracing

### Trace Configuration
```python
# tracing/config.py
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

def setup_tracing():
    # Create a TracerProvider
    provider = TracerProvider()
    
    # Create a JaegerExporter
    jaeger_exporter = JaegerExporter(
        agent_host_name="jaeger-agent",
        agent_port=6831,
    )
    
    # Add SpanProcessor to the TracerProvider
    provider.add_span_processor(
        BatchSpanProcessor(jaeger_exporter)
    )
    
    # Set the TracerProvider
    trace.set_tracer_provider(provider)
```

### Trace Implementation
```python
# tracing/tracer.py
from opentelemetry import trace
from functools import wraps

def trace_function(name=None):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            tracer = trace.get_tracer(__name__)
            with tracer.start_as_current_span(
                name or func.__name__
            ) as span:
                # Add attributes to span
                span.set_attribute(
                    "function.name",
                    func.__name__
                )
                span.set_attribute(
                    "function.args",
                    str(args)
                )
                
                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as e:
                    span.set_attribute(
                        "error",
                        str(e)
                    )
                    raise
        return wrapper
    return decorator
```

## Reporting

### Report Generation
```python
# reporting/generator.py
class ReportGenerator:
    def generate_report(self, timeframe: str):
        # Collect metrics
        metrics = self.collect_metrics(timeframe)
        
        # Generate insights
        insights = self.generate_insights(metrics)
        
        # Create report
        return self.format_report(metrics, insights)
    
    def collect_metrics(self, timeframe):
        return {
            'requests': self.get_request_metrics(),
            'errors': self.get_error_metrics(),
            'performance': self.get_performance_metrics(),
            'resources': self.get_resource_metrics()
        }
```

### Automated Reports
```python
# reporting/automation.py
from datetime import datetime, timedelta

class ReportAutomation:
    def schedule_reports(self):
        # Daily report
        self.schedule_daily_report()
        
        # Weekly report
        self.schedule_weekly_report()
        
        # Monthly report
        self.schedule_monthly_report()
    
    async def generate_daily_report(self):
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=1)
        
        report = await self.generate_report(
            start_time=start_time,
            end_time=end_time,
            report_type='daily'
        )
        
        await self.distribute_report(report)
```

## Best Practices

### 1. Metric Collection
- Use meaningful metric names
- Add appropriate labels
- Set proper buckets for histograms
- Monitor resource usage

### 2. Alert Configuration
- Set appropriate thresholds
- Configure proper routing
- Add clear descriptions
- Avoid alert fatigue

### 3. Dashboard Organization
- Group related metrics
- Use consistent naming
- Add documentation
- Regular updates

### 4. Log Management
- Structured logging
- Proper log levels
- Regular rotation
- Efficient querying
