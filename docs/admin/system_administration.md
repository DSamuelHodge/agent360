# Agent360 System Administration Guide

## Overview
This guide provides comprehensive instructions for administering and maintaining the Agent360 system.

## Table of Contents
1. [System Architecture](#system-architecture)
2. [User Management](#user-management)
3. [Resource Management](#resource-management)
4. [Monitoring and Alerting](#monitoring-and-alerting)
5. [Backup and Recovery](#backup-and-recovery)
6. [Security Management](#security-management)
7. [Performance Tuning](#performance-tuning)
8. [Troubleshooting](#troubleshooting)

## System Architecture

### Component Overview
- **Agent Runtime**: Core processing engine
- **Model Service**: LLM integration layer
- **Tools Layer**: Extensible tool framework
- **API Layer**: RESTful interface
- **Infrastructure**: Kubernetes-based deployment

### Dependencies
- Cassandra/Spanner: Primary database
- Redis: Caching and rate limiting
- Temporal: Workflow orchestration
- Prometheus/Grafana: Monitoring
- OpenTelemetry: Tracing

## User Management

### User Administration
```bash
# List users
kubectl exec -it agent360-admin -- python manage.py list-users

# Create admin user
kubectl exec -it agent360-admin -- python manage.py create-admin \
  --username admin \
  --email admin@example.com

# Reset user password
kubectl exec -it agent360-admin -- python manage.py reset-password \
  --username user123
```

### Role Management
```bash
# List roles
kubectl exec -it agent360-admin -- python manage.py list-roles

# Assign role
kubectl exec -it agent360-admin -- python manage.py assign-role \
  --username user123 \
  --role admin
```

## Resource Management

### Kubernetes Resources
```bash
# View resource usage
kubectl top nodes
kubectl top pods -n agent360

# Scale deployments
kubectl scale deployment agent360 \
  --namespace agent360 \
  --replicas=5

# Update resource limits
kubectl set resources deployment agent360 \
  --namespace agent360 \
  --limits=cpu=2,memory=4Gi \
  --requests=cpu=1,memory=2Gi
```

### Database Management
```bash
# Monitor database health
kubectl exec -it cassandra-0 -- nodetool status
kubectl exec -it cassandra-0 -- nodetool tablestats agent360

# Optimize database
kubectl exec -it cassandra-0 -- nodetool cleanup
kubectl exec -it cassandra-0 -- nodetool repair
```

### Cache Management
```bash
# Monitor Redis
kubectl exec -it redis-0 -- redis-cli info

# Clear cache
kubectl exec -it redis-0 -- redis-cli flushall

# Set cache policy
kubectl exec -it redis-0 -- redis-cli config set maxmemory-policy allkeys-lru
```

## Monitoring and Alerting

### Metrics Collection
```bash
# View metrics
curl -s http://localhost:9090/metrics | grep agent360

# Check alert status
curl -s http://localhost:9093/api/v2/alerts
```

### Log Management
```bash
# View logs
kubectl logs -f -l app=agent360 -n agent360

# Search logs
kubectl logs -f -l app=agent360 -n agent360 | grep ERROR

# Export logs
kubectl logs -l app=agent360 -n agent360 > agent360.log
```

### Alert Configuration
```yaml
# prometheus/alerts.yaml
groups:
  - name: agent360
    rules:
      - alert: HighErrorRate
        expr: rate(agent360_errors_total[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: High error rate detected
```

## Backup and Recovery

### Backup Procedures
```bash
# Manual backup
kubectl exec -it agent360-backup -- backup.sh

# Verify backup
kubectl exec -it agent360-backup -- verify-backup.sh

# List backups
kubectl exec -it agent360-backup -- list-backups.sh
```

### Recovery Procedures
```bash
# Restore from backup
kubectl exec -it agent360-backup -- restore.sh \
  --backup-id backup-20250111

# Verify restoration
kubectl exec -it agent360-backup -- verify-restore.sh

# Rollback if needed
kubectl exec -it agent360-backup -- rollback.sh
```

## Security Management

### Certificate Management
```bash
# Rotate certificates
kubectl create secret tls agent360-tls \
  --cert=new-cert.pem \
  --key=new-key.pem \
  --dry-run=client -o yaml | kubectl apply -f -

# View certificate expiry
kubectl get secret agent360-tls -o jsonpath='{.metadata.annotations.cert-expiry}'
```

### Access Control
```bash
# Review RBAC
kubectl auth can-i --list --namespace agent360

# Update RBAC
kubectl apply -f rbac/
```

### Security Scanning
```bash
# Run security scan
trivy image agent360:latest

# Run dependency scan
safety check
```

## Performance Tuning

### System Optimization
```bash
# Profile application
kubectl exec -it agent360-0 -- python -m cProfile app.py

# Analyze performance
kubectl exec -it agent360-0 -- python analyze_performance.py

# Tune parameters
kubectl apply -f config/tuning.yaml
```

### Cache Optimization
```bash
# Monitor cache hit rate
kubectl exec -it redis-0 -- redis-cli info stats | grep hit_rate

# Adjust cache size
kubectl exec -it redis-0 -- redis-cli config set maxmemory 2gb
```

### Query Optimization
```sql
-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM agent360.audit_logs
WHERE tenant_id = ? AND timestamp > ?;

-- Add indexes
CREATE INDEX ON agent360.audit_logs (tenant_id, timestamp);
```

## Troubleshooting

### Common Issues

1. Pod Startup Issues
```bash
# Check pod status
kubectl describe pod <pod-name> -n agent360

# Check events
kubectl get events -n agent360

# Check logs
kubectl logs <pod-name> -n agent360
```

2. Performance Issues
```bash
# Check resource usage
kubectl top pods -n agent360

# Profile application
kubectl exec -it <pod-name> -n agent360 -- python -m cProfile app.py

# Check network
kubectl exec -it <pod-name> -n agent360 -- netstat -an
```

3. Database Issues
```bash
# Check connectivity
kubectl exec -it <pod-name> -n agent360 -- nc -zv cassandra 9042

# Check logs
kubectl logs -l app=cassandra -n agent360

# Check metrics
kubectl exec -it cassandra-0 -- nodetool tablestats
```

### Diagnostic Tools
```bash
# Network diagnostics
kubectl exec -it <pod-name> -n agent360 -- tcpdump -i any

# System diagnostics
kubectl exec -it <pod-name> -n agent360 -- top -H

# Memory diagnostics
kubectl exec -it <pod-name> -n agent360 -- free -m
```

### Recovery Procedures

1. Service Recovery
```bash
# Restart service
kubectl rollout restart deployment agent360 -n agent360

# Verify recovery
kubectl rollout status deployment agent360 -n agent360
```

2. Data Recovery
```bash
# Backup data
kubectl exec -it cassandra-0 -- nodetool snapshot agent360

# Restore data
kubectl exec -it cassandra-0 -- nodetool restore
```

3. System Recovery
```bash
# Scale down
kubectl scale deployment agent360 --replicas=0 -n agent360

# Clean state
kubectl delete pvc --all -n agent360

# Scale up
kubectl scale deployment agent360 --replicas=3 -n agent360
```

## Best Practices

1. Regular Maintenance
- Schedule regular backups
- Monitor system health
- Update security patches
- Review logs and metrics

2. Documentation
- Keep configuration documented
- Document incidents and resolutions
- Maintain runbooks
- Update procedures regularly

3. Security
- Regular security audits
- Certificate rotation
- Access review
- Vulnerability scanning
