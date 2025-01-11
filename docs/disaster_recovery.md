# Disaster Recovery Procedures

## Overview
This document outlines the disaster recovery procedures for Agent360. It covers various failure scenarios and the steps to recover from them.

## Recovery Time Objectives (RTO)
- Critical services: < 1 hour
- Non-critical services: < 4 hours

## Recovery Point Objectives (RPO)
- Database: < 5 minutes
- Event streams: < 1 minute
- Configuration: < 24 hours

## Failure Scenarios

### 1. Data Center Failure
#### Detection
- Monitoring alerts from multiple services
- Health check failures
- Network connectivity issues

#### Recovery Steps
1. Activate secondary data center
```bash
kubectl config use-context dr-cluster
kubectl apply -f k8s/dr/
```

2. Verify DNS failover
```bash
dig +short agent360.example.com
```

3. Verify data replication
```bash
temporal admin cluster verify-replication
```

### 2. Database Failure
#### Detection
- Cassandra node health alerts
- Query latency increases
- Connection errors

#### Recovery Steps
1. Check node status
```bash
nodetool status
```

2. Repair inconsistent nodes
```bash
nodetool repair -pr
```

3. Replace failed nodes if necessary
```bash
kubectl -n agent360 delete pod cassandra-X
kubectl -n agent360 wait --for=condition=Ready pod/cassandra-X
```

### 3. Cache Failure
#### Detection
- Redis sentinel alerts
- Cache hit rate decrease
- Connection timeouts

#### Recovery Steps
1. Verify sentinel status
```bash
redis-cli -h sentinel info sentinel
```

2. Trigger failover if needed
```bash
redis-cli -h sentinel sentinel failover mymaster
```

3. Clear and rebuild cache
```bash
kubectl exec -it redis-cli -- flushall
```

### 4. Message Queue Failure
#### Detection
- Redpanda metrics alerts
- Message lag increase
- Producer/consumer errors

#### Recovery Steps
1. Check cluster health
```bash
rpk cluster health
```

2. Recover failed topics
```bash
rpk topic recover <topic-name>
```

### 5. Application Failure
#### Detection
- Pod crash alerts
- API error rate increase
- Resource exhaustion

#### Recovery Steps
1. Scale down affected deployments
```bash
kubectl scale deployment agent360 --replicas=0
```

2. Clear problematic state
```bash
kubectl delete pvc data-agent360-0
```

3. Restore from backup
```bash
./backup/restore.sh <backup-id>
```

4. Scale up gradually
```bash
kubectl scale deployment agent360 --replicas=1
sleep 60
kubectl scale deployment agent360 --replicas=3
```

## Backup Recovery

### Full System Recovery
1. Stop all services
```bash
kubectl scale deployment --all --replicas=0
```

2. Restore data stores
```bash
./backup/restore-cassandra.sh <backup-id>
./backup/restore-redis.sh <backup-id>
./backup/restore-temporal.sh <backup-id>
```

3. Verify data integrity
```bash
./scripts/verify-integrity.sh
```

4. Restart services
```bash
kubectl apply -f k8s/base/
```

### Partial Recovery
1. Identify affected components
```bash
./scripts/health-check.sh
```

2. Restore specific components
```bash
./backup/restore-component.sh <component> <backup-id>
```

## Testing and Validation

### Regular Testing
1. Quarterly DR drills
2. Monthly backup restoration tests
3. Weekly failover tests

### Validation Checklist
- [ ] All services running
- [ ] Data integrity verified
- [ ] Replication working
- [ ] Performance metrics normal
- [ ] Security controls active

## Communication Plan

### Internal Communication
1. Alert on-call team
2. Update status page
3. Notify stakeholders
4. Document incident

### External Communication
1. Update status page
2. Send customer notifications
3. Provide regular updates
4. Post incident report
