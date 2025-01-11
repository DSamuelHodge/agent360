"""
Performance tests for Agent360 using Locust.
"""
from locust import HttpUser, task, between
from typing import Dict, Any
import json
import random

class Agent360User(HttpUser):
    """Simulated user for load testing."""
    
    wait_time = between(1, 3)
    
    def on_start(self):
        """Setup before tests."""
        # Login and get token
        response = self.client.post("/api/v1/auth/token", json={
            "username": "test_user",
            "password": "test_password"
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
    @task(3)
    def execute_simple_query(self):
        """Test simple query execution."""
        payload = {
            "input": {
                "query": "What is the weather?",
                "tools": ["rest_tool"]
            },
            "timeout": 30
        }
        self.client.post(
            "/api/v1/agent/execute",
            json=payload,
            headers=self.headers
        )
        
    @task(2)
    def execute_complex_query(self):
        """Test complex query with multiple tools."""
        payload = {
            "input": {
                "query": "Get user data and analyze trends",
                "tools": ["database_tool", "rest_tool"]
            },
            "timeout": 60
        }
        self.client.post(
            "/api/v1/agent/execute",
            json=payload,
            headers=self.headers
        )
        
    @task(1)
    def execute_rag_query(self):
        """Test RAG functionality."""
        payload = {
            "input": {
                "query": "Find similar documents",
                "tools": ["rag_tool"],
                "parameters": {
                    "k": 5,
                    "threshold": 0.7
                }
            },
            "timeout": 45
        }
        self.client.post(
            "/api/v1/agent/execute",
            json=payload,
            headers=self.headers
        )
        
    @task
    def list_tools(self):
        """Test tool listing endpoint."""
        self.client.get(
            "/api/v1/agent/tools",
            headers=self.headers
        )
        
    @task
    def health_check(self):
        """Test health check endpoint."""
        self.client.get("/health")
