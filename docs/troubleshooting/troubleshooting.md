# Agent360 Troubleshooting Guide

## Overview
This guide provides comprehensive troubleshooting procedures for Agent360.

## Table of Contents
1. [Common Issues](#common-issues)
2. [Diagnostic Tools](#diagnostic-tools)
3. [Performance Issues](#performance-issues)
4. [Network Issues](#network-issues)
5. [Database Issues](#database-issues)
6. [Application Issues](#application-issues)
7. [Security Issues](#security-issues)

## Common Issues

### 1. Service Startup Issues
```bash
# Check pod status
kubectl get pods -n agent360

# View pod logs
kubectl logs <pod-name> -n agent360

# Check events
kubectl get events -n agent360 --sort-by='.lastTimestamp'
```

### 2. Connection Issues
```bash
# Check service endpoints
kubectl get endpoints -n agent360

# Test network connectivity
kubectl exec -it <pod-name> -n agent360 -- nc -zv <service-name> <port>

# View service logs
kubectl logs -l app=agent360 -n agent360 | grep "connection"
```

### 3. Resource Issues
```bash
# Check resource usage
kubectl top pods -n agent360

# View node resources
kubectl describe node <node-name>

# Check resource quotas
kubectl describe resourcequota -n agent360
```

## Diagnostic Tools

### System Diagnostics
```python
# diagnostics/system.py
class SystemDiagnostics:
    def collect_diagnostics(self):
        return {
            "system_info": self.get_system_info(),
            "resource_usage": self.get_resource_usage(),
            "network_status": self.get_network_status(),
            "process_list": self.get_process_list()
        }
    
    def get_system_info(self):
        import psutil
        return {
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "disk_usage": psutil.disk_usage('/'),
            "boot_time": psutil.boot_time()
        }
```

### Log Analysis
```python
# diagnostics/logs.py
class LogAnalyzer:
    def analyze_logs(self, timeframe: str):
        # Collect logs
        logs = self.collect_logs(timeframe)
        
        # Analyze patterns
        patterns = self.identify_patterns(logs)
        
        # Generate insights
        return self.generate_insights(patterns)
    
    def identify_patterns(self, logs: List[str]):
        import re
        patterns = {
            "errors": len(re.findall(r'ERROR', '\n'.join(logs))),
            "warnings": len(re.findall(r'WARN', '\n'.join(logs))),
            "exceptions": len(re.findall(r'Exception', '\n'.join(logs)))
        }
        return patterns
```

### Network Diagnostics
```python
# diagnostics/network.py
class NetworkDiagnostics:
    def diagnose_network(self):
        results = {
            "connectivity": self.check_connectivity(),
            "latency": self.measure_latency(),
            "dns": self.check_dns(),
            "ports": self.check_ports()
        }
        return results
    
    def measure_latency(self):
        import socket
        import time
        
        latencies = {}
        for service in self.get_services():
            start = time.time()
            try:
                socket.create_connection((service, 80), timeout=5)
                latencies[service] = time.time() - start
            except:
                latencies[service] = None
        return latencies
```

## Performance Issues

### Memory Leaks
```python
# performance/memory.py
class MemoryAnalyzer:
    def analyze_memory(self):
        import tracemalloc
        tracemalloc.start()
        
        # Run operations
        self.run_test_operations()
        
        # Get snapshot
        snapshot = tracemalloc.take_snapshot()
        
        return self.analyze_snapshot(snapshot)
    
    def analyze_snapshot(self, snapshot):
        top_stats = snapshot.statistics('lineno')
        return [{
            "file": stat.traceback[0].filename,
            "line": stat.traceback[0].lineno,
            "size": stat.size
        } for stat in top_stats[:10]]
```

### CPU Bottlenecks
```python
# performance/cpu.py
class CPUAnalyzer:
    def profile_cpu(self, duration: int):
        import cProfile
        import pstats
        
        profiler = cProfile.Profile()
        profiler.enable()
        
        # Run operations
        self.run_test_operations()
        
        profiler.disable()
        stats = pstats.Stats(profiler)
        
        return stats.sort_stats('cumulative').print_stats(20)
```

### Slow Queries
```python
# performance/database.py
class QueryAnalyzer:
    def analyze_slow_queries(self):
        from datetime import datetime, timedelta
        
        # Get slow query log
        slow_queries = self.get_slow_queries(
            start_time=datetime.now() - timedelta(hours=1)
        )
        
        # Analyze patterns
        return self.analyze_query_patterns(slow_queries)
    
    def analyze_query_patterns(self, queries):
        patterns = {}
        for query in queries:
            pattern = self.normalize_query(query)
            patterns[pattern] = patterns.get(pattern, 0) + 1
        return patterns
```

## Network Issues

### Connectivity Problems
```python
# network/connectivity.py
class ConnectivityTester:
    def test_connectivity(self):
        results = {
            "internal": self.test_internal_connectivity(),
            "external": self.test_external_connectivity(),
            "dns": self.test_dns_resolution()
        }
        return results
    
    def test_internal_connectivity(self):
        services = [
            "database",
            "cache",
            "queue"
        ]
        return {
            service: self.ping_service(service)
            for service in services
        }
```

### Service Discovery
```python
# network/discovery.py
class ServiceDiscovery:
    def check_service_discovery(self):
        import dns.resolver
        
        services = self.get_service_list()
        results = {}
        
        for service in services:
            try:
                answers = dns.resolver.resolve(
                    f"{service}.agent360.svc.cluster.local",
                    'A'
                )
                results[service] = [str(rdata) for rdata in answers]
            except:
                results[service] = None
        
        return results
```

### Load Balancing
```python
# network/loadbalancer.py
class LoadBalancerDiagnostics:
    def check_load_balancer(self):
        return {
            "health": self.check_lb_health(),
            "distribution": self.check_traffic_distribution(),
            "sessions": self.check_session_persistence()
        }
    
    def check_traffic_distribution(self):
        from collections import Counter
        
        # Get traffic logs
        traffic = self.get_traffic_logs()
        
        # Analyze distribution
        return Counter(
            request['backend']
            for request in traffic
        )
```

## Database Issues

### Connection Problems
```python
# database/connection.py
class DatabaseConnectionTester:
    def test_database_connection(self):
        results = {
            "connection": self.test_connection(),
            "authentication": self.test_authentication(),
            "permissions": self.test_permissions()
        }
        return results
    
    def test_connection(self):
        try:
            self.db.execute("SELECT 1")
            return True
        except Exception as e:
            return str(e)
```

### Data Consistency
```python
# database/consistency.py
class ConsistencyChecker:
    def check_consistency(self):
        results = {
            "replication": self.check_replication(),
            "constraints": self.check_constraints(),
            "indexes": self.check_indexes()
        }
        return results
    
    def check_replication(self):
        # Check replication lag
        lag = self.get_replication_lag()
        
        # Check consistency level
        consistency = self.get_consistency_level()
        
        return {
            "lag": lag,
            "consistency_level": consistency
        }
```

## Application Issues

### Error Handling
```python
# application/errors.py
class ErrorAnalyzer:
    def analyze_errors(self):
        # Collect error logs
        errors = self.collect_error_logs()
        
        # Categorize errors
        categorized = self.categorize_errors(errors)
        
        # Generate report
        return self.generate_error_report(categorized)
    
    def categorize_errors(self, errors):
        categories = {
            "validation": [],
            "authentication": [],
            "authorization": [],
            "system": []
        }
        
        for error in errors:
            category = self.determine_category(error)
            categories[category].append(error)
        
        return categories
```

### State Management
```python
# application/state.py
class StateAnalyzer:
    def analyze_state(self):
        return {
            "memory": self.analyze_memory_state(),
            "cache": self.analyze_cache_state(),
            "sessions": self.analyze_session_state()
        }
    
    def analyze_cache_state(self):
        # Check cache hit rate
        hit_rate = self.get_cache_hit_rate()
        
        # Check cache size
        size = self.get_cache_size()
        
        # Check cache entries
        entries = self.get_cache_entries()
        
        return {
            "hit_rate": hit_rate,
            "size": size,
            "entries": len(entries)
        }
```

## Security Issues

### Access Control
```python
# security/access.py
class AccessAnalyzer:
    def analyze_access_patterns(self):
        # Get access logs
        logs = self.get_access_logs()
        
        # Analyze patterns
        patterns = self.analyze_patterns(logs)
        
        # Check for anomalies
        anomalies = self.detect_anomalies(patterns)
        
        return {
            "patterns": patterns,
            "anomalies": anomalies
        }
```

### Authentication
```python
# security/auth.py
class AuthenticationTester:
    def test_authentication(self):
        results = {
            "login": self.test_login(),
            "token": self.test_token_validation(),
            "session": self.test_session_management()
        }
        return results
    
    def test_token_validation(self):
        # Test valid token
        valid = self.validate_token(self.generate_valid_token())
        
        # Test expired token
        expired = self.validate_token(self.generate_expired_token())
        
        # Test invalid token
        invalid = self.validate_token("invalid_token")
        
        return {
            "valid": valid,
            "expired": expired,
            "invalid": invalid
        }
```

## Best Practices

### 1. Systematic Approach
- Identify symptoms
- Collect evidence
- Analyze patterns
- Test hypotheses
- Implement solution
- Verify fix

### 2. Documentation
- Document issues
- Record solutions
- Update procedures
- Share knowledge

### 3. Prevention
- Monitor metrics
- Set up alerts
- Regular maintenance
- Proactive testing

### 4. Communication
- Clear updates
- Regular status
- Stakeholder management
- Knowledge sharing
