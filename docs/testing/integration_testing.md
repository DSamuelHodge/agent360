# Agent360 Integration Testing Guide

## Overview
This guide outlines the integration testing strategy and implementation for Agent360.

## Table of Contents
1. [Testing Strategy](#testing-strategy)
2. [Test Environment Setup](#test-environment-setup)
3. [Test Implementation](#test-implementation)
4. [Test Execution](#test-execution)
5. [CI/CD Integration](#cicd-integration)
6. [Best Practices](#best-practices)

## Testing Strategy

### Test Levels
1. **Component Integration Tests**
   - Model Service integration
   - Tool integration
   - Database integration
   
2. **System Integration Tests**
   - End-to-end workflows
   - API integration
   - External service integration

3. **Performance Tests**
   - Load testing
   - Stress testing
   - Endurance testing

### Test Coverage
```python
# Example test coverage configuration
coverage_config = {
    "source": ["src/"],
    "omit": [
        "*/tests/*",
        "*/migrations/*"
    ],
    "branch": True,
    "fail_under": 80
}
```

## Test Environment Setup

### Local Environment
```bash
# Create test environment
python -m venv test-env
source test-env/bin/activate

# Install dependencies
pip install -r requirements-test.txt

# Setup test database
docker-compose -f docker-compose.test.yml up -d
```

### Test Configuration
```yaml
# test_config.yaml
test:
  database:
    host: localhost
    port: 9042
    keyspace: agent360_test
  redis:
    host: localhost
    port: 6379
  model_service:
    endpoint: http://localhost:8001
    api_key: test_key
```

## Test Implementation

### Component Tests

```python
# test_model_service.py
import pytest
from src.agent_runtime.model_service import ModelService

class TestModelService:
    @pytest.fixture
    def model_service(self):
        return ModelService(config={
            "model": "gpt-4",
            "temperature": 0.7
        })
    
    async def test_model_generation(self, model_service):
        prompt = "Test prompt"
        result = await model_service.generate(prompt)
        assert result is not None
        assert isinstance(result, str)
    
    async def test_model_error_handling(self, model_service):
        with pytest.raises(Exception):
            await model_service.generate(None)
```

### Integration Tests

```python
# test_workflow.py
import pytest
from src.agent_runtime.orchestrator import Orchestrator

class TestWorkflow:
    @pytest.fixture
    async def orchestrator(self):
        return await Orchestrator.create()
    
    async def test_complete_workflow(self, orchestrator):
        input_data = {
            "query": "Test query",
            "tools": ["rest_tool"]
        }
        
        result = await orchestrator.process_step(input_data)
        assert result["status"] == "success"
        assert "output" in result
```

### API Tests

```python
# test_api.py
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_execute_agent():
    response = client.post(
        "/agent/execute",
        json={
            "query": "Test query",
            "tools": ["rest_tool"]
        }
    )
    assert response.status_code == 200
    assert "output" in response.json()
```

## Test Execution

### Running Tests
```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_workflow.py

# Run with coverage
pytest --cov=src tests/

# Generate coverage report
coverage html
```

### Test Parameters
```python
# conftest.py
import pytest

def pytest_addoption(parser):
    parser.addoption(
        "--environment",
        default="test",
        help="Environment to run tests against"
    )

@pytest.fixture
def environment(request):
    return request.config.getoption("--environment")
```

## CI/CD Integration

### GitHub Actions

```yaml
# .github/workflows/integration-tests.yml
name: Integration Tests

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      cassandra:
        image: cassandra:latest
        ports:
          - 9042:9042
      redis:
        image: redis:latest
        ports:
          - 6379:6379
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements-test.txt
    
    - name: Run tests
      run: |
        pytest --cov=src tests/
        coverage xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v2
```

## Best Practices

### 1. Test Organization

```plaintext
tests/
├── integration/
│   ├── test_workflow.py
│   ├── test_api.py
│   └── test_tools.py
├── performance/
│   ├── test_load.py
│   └── test_stress.py
├── conftest.py
└── pytest.ini
```

### 2. Test Data Management

```python
# test_data.py
import json
from pathlib import Path

class TestData:
    @staticmethod
    def load_fixture(name: str):
        path = Path(__file__).parent / "fixtures" / f"{name}.json"
        with path.open() as f:
            return json.load(f)
    
    @staticmethod
    async def setup_test_data(database):
        data = TestData.load_fixture("test_data")
        await database.bulk_insert(data)
```

### 3. Mocking External Services

```python
# test_external_service.py
from unittest.mock import patch
import pytest

class TestExternalService:
    @pytest.fixture
    def mock_response(self):
        return {
            "status": "success",
            "data": {"key": "value"}
        }
    
    @patch("src.tools.rest_tool.RESTTool.execute")
    async def test_external_call(self, mock_execute, mock_response):
        mock_execute.return_value = mock_response
        
        # Test implementation
        result = await service.call_external()
        assert result == mock_response
```

### 4. Error Scenario Testing

```python
# test_error_handling.py
import pytest
from src.exceptions import AgentError

class TestErrorHandling:
    async def test_invalid_input(self, client):
        response = client.post(
            "/agent/execute",
            json={"invalid": "data"}
        )
        assert response.status_code == 400
        
    async def test_service_error(self, orchestrator):
        with pytest.raises(AgentError):
            await orchestrator.process_step({"invalid": "step"})
```

### 5. Performance Testing

```python
# test_performance.py
import asyncio
import time
from locust import HttpUser, task, between

class Agent360User(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def execute_agent(self):
        self.client.post(
            "/agent/execute",
            json={
                "query": "Test query",
                "tools": ["rest_tool"]
            }
        )
```

### 6. Test Reporting

```python
# pytest.ini
[pytest]
addopts = --verbose
          --html=report.html
          --self-contained-html
          --cov=src
          --cov-report=html
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

### 7. Continuous Monitoring

```python
# test_monitoring.py
import prometheus_client
import pytest

class TestMonitoring:
    async def test_metrics_collection(self, client):
        # Generate some test load
        for _ in range(10):
            await client.post("/agent/execute", ...)
        
        # Check metrics
        metrics = prometheus_client.REGISTRY.get_sample_value(
            'agent360_requests_total'
        )
        assert metrics >= 10
```
