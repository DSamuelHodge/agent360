"""
Performance tests for Agent360 using Locust.
"""
from locust import HttpUser, task, between, events
from typing import Dict, Any
import json
import random
import time

class AuthenticationUser(HttpUser):
    """Simulated user for authentication load testing."""
    
    wait_time = between(0.1, 0.5)  # Reduced wait time for auth testing
    host = "http://localhost:8000"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.auth_success = 0
        self.auth_failure = 0
        self.total_latency = 0
        
    @task(1)
    def authenticate(self):
        """Test authentication performance."""
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
                self.auth_success += 1
            else:
                self.auth_failure += 1
                
            latency = (time.time() - start_time) * 1000  # Convert to ms
            self.total_latency += latency
            
            # Log detailed metrics
            self.environment.events.request.fire(
                request_type="POST",
                name="/api/v1/auth/token",
                response_time=latency,
                response_length=len(response.content),
                response=response,
                context={
                    "success": response.status_code == 200,
                    "latency_ms": latency
                }
            )
            
        except Exception as e:
            self.auth_failure += 1
            self.environment.events.request_failure.fire(
                request_type="POST",
                name="/api/v1/auth/token",
                response_time=0,
                exception=e
            )
            
    def on_stop(self):
        """Report metrics when test stops."""
        total_requests = self.auth_success + self.auth_failure
        if total_requests > 0:
            avg_latency = self.total_latency / total_requests
            success_rate = (self.auth_success / total_requests) * 100
            
            print("\nAuthentication Performance Metrics:")
            print(f"Total Requests: {total_requests}")
            print(f"Successful Authentications: {self.auth_success}")
            print(f"Failed Authentications: {self.auth_failure}")
            print(f"Average Latency: {avg_latency:.2f}ms")
            print(f"Success Rate: {success_rate:.2f}%")

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Setup before test starts."""
    print("Starting Authentication Performance Test")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Cleanup after test ends."""
    print("\nAuthentication Performance Test Complete")
