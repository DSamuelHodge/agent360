# Agent360 High Availability Guide

## Overview
This guide outlines the high availability (HA) architecture and implementation for Agent360.

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Component Redundancy](#component-redundancy)
3. [Data Replication](#data-replication)
4. [Load Balancing](#load-balancing)
5. [Failover Strategies](#failover-strategies)
6. [Monitoring and Alerts](#monitoring-and-alerts)
7. [Disaster Recovery](#disaster-recovery)

## Architecture Overview

### High-Level Architecture
```plaintext
[Client] → [Load Balancer] → [API Gateway]
                                   ↓
[Service Mesh] → [Agent Services (Multiple Replicas)]
                                   ↓
[Database Cluster] ← → [Cache Cluster] ← → [Message Queue]
```

### Availability Zones
```yaml
# kubernetes/multi-az.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agent360
spec:
  replicas: 6
  strategy:
    type: RollingUpdate
  template:
    spec:
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: agent360
```

## Component Redundancy

### Application Layer
```yaml
# kubernetes/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agent360
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    spec:
      containers:
      - name: agent360
        image: agent360:latest
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
```

### Database Layer
```yaml
# cassandra/statefulset.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: cassandra
spec:
  replicas: 3
  serviceName: cassandra
  template:
    spec:
      containers:
      - name: cassandra
        image: cassandra:latest
        env:
        - name: CASSANDRA_SEEDS
          value: "cassandra-0.cassandra.default.svc.cluster.local"
        - name: CASSANDRA_CLUSTER_NAME
          value: "agent360-cluster"
```

### Cache Layer
```yaml
# redis/sentinel.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: redis-sentinel
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: redis-sentinel
        image: redis:latest
        args:
        - "--sentinel"
        - "monitor"
        - "mymaster"
        - "redis-0.redis"
        - "6379"
        - "2"
```

## Data Replication

### Database Replication
```python
# database/replication.py
from cassandra.cluster import Cluster

class DatabaseReplication:
    def configure_replication(self):
        cluster = Cluster(['cassandra-0', 'cassandra-1', 'cassandra-2'])
        session = cluster.connect()
        
        # Configure replication strategy
        session.execute("""
            ALTER KEYSPACE agent360
            WITH REPLICATION = {
                'class': 'NetworkTopologyStrategy',
                'dc1': 3,
                'dc2': 3
            }
        """)
```

### Cache Replication
```python
# cache/replication.py
import redis
from redis.sentinel import Sentinel

class CacheReplication:
    def __init__(self):
        self.sentinel = Sentinel([
            ('redis-sentinel-0', 26379),
            ('redis-sentinel-1', 26379),
            ('redis-sentinel-2', 26379)
        ])
    
    def get_master(self):
        return self.sentinel.master_for('mymaster')
    
    def get_slave(self):
        return self.sentinel.slave_for('mymaster')
```

## Load Balancing

### Service Mesh Configuration
```yaml
# istio/virtualservice.yaml
apiVersion: networking.istio.io/v1alpha3
kind: VirtualService
metadata:
  name: agent360
spec:
  hosts:
  - agent360.example.com
  http:
  - route:
    - destination:
        host: agent360
        subset: v1
      weight: 90
    - destination:
        host: agent360
        subset: v2
      weight: 10
```

### Load Balancer Configuration
```yaml
# kubernetes/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: agent360
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: nlb
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 8080
  selector:
    app: agent360
```

## Failover Strategies

### Application Failover
```python
# failover/app.py
class FailoverManager:
    def handle_node_failure(self, node_id: str):
        # Detect node failure
        if not self.is_node_healthy(node_id):
            # Drain connections
            self.drain_connections(node_id)
            
            # Redirect traffic
            self.update_load_balancer()
            
            # Start replacement node
            self.start_replacement_node()
```

### Database Failover
```python
# failover/database.py
class DatabaseFailover:
    def handle_primary_failure(self):
        # Detect primary failure
        if not self.is_primary_healthy():
            # Elect new primary
            new_primary = self.elect_new_primary()
            
            # Update connection strings
            self.update_connection_config(new_primary)
            
            # Notify applications
            self.notify_apps_of_failover()
```

### Cache Failover
```python
# failover/cache.py
class CacheFailover:
    def handle_master_failure(self):
        # Sentinel automatically promotes slave to master
        new_master = self.sentinel.discover_master('mymaster')
        
        # Update application connections
        self.update_cache_connections(new_master)
```

## Monitoring and Alerts

### Health Checks
```python
# monitoring/health.py
class HealthChecker:
    def check_component_health(self):
        health_status = {
            "app": self.check_app_health(),
            "database": self.check_db_health(),
            "cache": self.check_cache_health(),
            "queue": self.check_queue_health()
        }
        
        return health_status
```

### Alert Configuration
```yaml
# prometheus/alerts.yaml
groups:
- name: availability
  rules:
  - alert: HighErrorRate
    expr: sum(rate(http_requests_total{status=~"5.."}[5m])) 
          / sum(rate(http_requests_total[5m])) > 0.1
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: High error rate detected
  
  - alert: PodRestart
    expr: changes(kube_pod_container_status_restarts_total{pod=~"agent360.*"}[1h]) > 3
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: Multiple pod restarts detected
```

## Disaster Recovery

### Backup Strategy
```python
# backup/strategy.py
class BackupManager:
    def perform_backup(self):
        # Backup database
        self.backup_database()
        
        # Backup configuration
        self.backup_config()
        
        # Verify backup
        self.verify_backup()
    
    def backup_database(self):
        # Create consistent snapshot
        snapshot_id = self.create_snapshot()
        
        # Copy to backup storage
        self.copy_to_storage(snapshot_id)
```

### Recovery Procedures
```python
# recovery/procedures.py
class DisasterRecovery:
    def recover_from_disaster(self):
        # Stop affected services
        self.stop_services()
        
        # Restore from backup
        self.restore_from_backup()
        
        # Verify data integrity
        self.verify_data()
        
        # Resume services
        self.resume_services()
```

## Best Practices

### 1. Regular Testing
- Failover testing
- Disaster recovery drills
- Load testing

### 2. Documentation
- Recovery procedures
- Configuration changes
- Incident history

### 3. Monitoring
- Real-time metrics
- Predictive analytics
- Capacity planning

### 4. Automation
- Automated failover
- Self-healing systems
- Automated testing
