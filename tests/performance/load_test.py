"""
Performance and load testing suite for Agent360.
Implements comprehensive testing scenarios for authentication, workflows, and system performance.
"""
from locust import HttpUser, task, between, events
from typing import Dict, Any
import json
import time
import random
from datetime import datetime

class Agent360LoadTest(HttpUser):
    """Load test simulation for Agent360 platform."""
    
    wait_time = between(1, 3)  # Think time between requests
    host = "http://localhost:8000"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = None
        self.workflow_ids = []
        # Metrics tracking
        self.auth_latency = []
        self.workflow_latency = []
        self.status_latency = []
    
    def on_start(self):
        """Setup before starting tests."""
        self._authenticate()
    
    def _authenticate(self):
        """Perform authentication and store token."""
        start_time = time.time()
        try:
            response = self.client.post(
                "/api/v1/auth/token",
                data={
                    "username": "test_user",
                    "password": "test_password",
                    "scope": "default"
                }
            )
            if response.status_code == 200:
                self.token = response.json()["access_token"]
                latency = (time.time() - start_time) * 1000
                self.auth_latency.append(latency)
                self.log_metric("auth_success", latency)
            else:
                self.log_metric("auth_failure", 0)
                
        except Exception as e:
            self.log_metric("auth_error", 0, error=str(e))
    
    @task(3)
    def execute_chain_workflow(self):
        """Test chain-of-thought workflow execution."""
        if not self.token:
            self._authenticate()
            
        start_time = time.time()
        payload = {
            "workflow_type": "chain_of_thought",
            "input": {
                "query": "Complex analysis task",
                "tools": ["rest_tool", "database_tool"],
                "parameters": {
                    "max_steps": 5,
                    "timeout": 30
                }
            }
        }
        
        try:
            response = self.client.post(
                "/api/v1/workflows/execute",
                json=payload,
                headers={"Authorization": f"Bearer {self.token}"}
            )
            
            latency = (time.time() - start_time) * 1000
            self.workflow_latency.append(latency)
            
            if response.status_code == 200:
                workflow_id = response.json().get("workflow_id")
                if workflow_id:
                    self.workflow_ids.append(workflow_id)
                self.log_metric("workflow_success", latency)
            else:
                self.log_metric("workflow_failure", latency)
                
        except Exception as e:
            self.log_metric("workflow_error", 0, error=str(e))
    
    @task(1)
    def execute_reflective_workflow(self):
        """Test reflective execution workflow."""
        if not self.token:
            self._authenticate()
            
        start_time = time.time()
        payload = {
            "workflow_type": "reflective_execution",
            "input": {
                "query": "Multi-step reasoning task",
                "max_iterations": 3,
                "parameters": {
                    "reflection_depth": 2,
                    "timeout": 45
                }
            }
        }
        
        try:
            response = self.client.post(
                "/api/v1/workflows/execute",
                json=payload,
                headers={"Authorization": f"Bearer {self.token}"}
            )
            
            latency = (time.time() - start_time) * 1000
            self.workflow_latency.append(latency)
            
            if response.status_code == 200:
                workflow_id = response.json().get("workflow_id")
                if workflow_id:
                    self.workflow_ids.append(workflow_id)
                self.log_metric("reflective_success", latency)
            else:
                self.log_metric("reflective_failure", latency)
                
        except Exception as e:
            self.log_metric("reflective_error", 0, error=str(e))
    
    @task(2)
    def check_workflow_status(self):
        """Test workflow status endpoint."""
        if not self.token or not self.workflow_ids:
            return
            
        workflow_id = random.choice(self.workflow_ids)
        start_time = time.time()
        
        try:
            response = self.client.get(
                f"/api/v1/workflows/status/{workflow_id}",
                headers={"Authorization": f"Bearer {self.token}"}
            )
            
            latency = (time.time() - start_time) * 1000
            self.status_latency.append(latency)
            
            if response.status_code == 200:
                self.log_metric("status_success", latency)
            else:
                self.log_metric("status_failure", latency)
                
        except Exception as e:
            self.log_metric("status_error", 0, error=str(e))
    
    def log_metric(self, name: str, latency: float, error: str = None):
        """Log performance metrics."""
        self.environment.events.request.fire(
            request_type="METRIC",
            name=name,
            response_time=latency,
            response_length=0,
            exception=error,
            context={
                "timestamp": datetime.now().isoformat(),
                "user_count": self.environment.runner.user_count
            }
        )

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Initialize test metrics."""
    print(f"\nStarting Load Test at {datetime.now().isoformat()}")
    print("Test Configuration:")
    print(f"- Host: {environment.host}")
    print(f"- User classes: {[user.__name__ for user in environment.user_classes]}")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Aggregate and report test metrics."""
    print(f"\nLoad Test Completed at {datetime.now().isoformat()}")
    
    # Aggregate metrics from all users
    total_auth_latency = []
    total_workflow_latency = []
    total_status_latency = []
    
    for user in environment.runner.user_greenlets:
        if hasattr(user, 'user_greenlet'):
            user_instance = user.user_greenlet.args[0]
            total_auth_latency.extend(user_instance.auth_latency)
            total_workflow_latency.extend(user_instance.workflow_latency)
            total_status_latency.extend(user_instance.status_latency)
    
    def calculate_percentiles(latencies):
        if not latencies:
            return None
        sorted_latencies = sorted(latencies)
        return {
            "p50": sorted_latencies[len(sorted_latencies) // 2],
            "p90": sorted_latencies[int(len(sorted_latencies) * 0.9)],
            "p95": sorted_latencies[int(len(sorted_latencies) * 0.95)],
            "p99": sorted_latencies[int(len(sorted_latencies) * 0.99)]
        }
    
    print("\nPerformance Metrics Summary:")
    print("\nAuthentication Latency (ms):")
    auth_percentiles = calculate_percentiles(total_auth_latency)
    if auth_percentiles:
        print(f"- Median (P50): {auth_percentiles['p50']:.2f}")
        print(f"- P90: {auth_percentiles['p90']:.2f}")
        print(f"- P95: {auth_percentiles['p95']:.2f}")
        print(f"- P99: {auth_percentiles['p99']:.2f}")
    
    print("\nWorkflow Execution Latency (ms):")
    workflow_percentiles = calculate_percentiles(total_workflow_latency)
    if workflow_percentiles:
        print(f"- Median (P50): {workflow_percentiles['p50']:.2f}")
        print(f"- P90: {workflow_percentiles['p90']:.2f}")
        print(f"- P95: {workflow_percentiles['p95']:.2f}")
        print(f"- P99: {workflow_percentiles['p99']:.2f}")
    
    print("\nStatus Check Latency (ms):")
    status_percentiles = calculate_percentiles(total_status_latency)
    if status_percentiles:
        print(f"- Median (P50): {status_percentiles['p50']:.2f}")
        print(f"- P90: {status_percentiles['p90']:.2f}")
        print(f"- P95: {status_percentiles['p95']:.2f}")
        print(f"- P99: {status_percentiles['p99']:.2f}")
