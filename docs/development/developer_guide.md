# Agent360 Developer Guide

## Overview
This guide provides comprehensive information for developers working on Agent360.

## Table of Contents
1. [Development Setup](#development-setup)
2. [Code Standards](#code-standards)
3. [CI/CD Pipeline](#cicd-pipeline)
4. [Testing Guidelines](#testing-guidelines)
5. [Contributing Guidelines](#contributing-guidelines)
6. [Documentation](#documentation)

## Development Setup

### Environment Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Setup pre-commit hooks
pre-commit install
```

### Configuration
```yaml
# config/development.yaml
environment: development
debug: true

database:
  host: localhost
  port: 9042
  keyspace: agent360_dev

redis:
  host: localhost
  port: 6379

model_service:
  endpoint: http://localhost:8001
  api_key: dev_key
```

### Local Development
```python
# scripts/dev_server.py
import uvicorn
from agent360.main import app

if __name__ == "__main__":
    uvicorn.run(
        "agent360.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="debug"
    )
```

## Code Standards

### Python Style Guide
```python
# examples/style_guide.py
from typing import Dict, List, Optional
from datetime import datetime

class UserManager:
    """
    Manages user operations.
    
    Attributes:
        db_client: Database client instance
        cache_client: Cache client instance
    """
    
    def __init__(
        self,
        db_client: DatabaseClient,
        cache_client: Optional[CacheClient] = None
    ):
        self.db_client = db_client
        self.cache_client = cache_client
    
    async def get_user(self, user_id: str) -> Dict:
        """
        Get user by ID.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dict containing user information
            
        Raises:
            UserNotFoundError: If user doesn't exist
        """
        # Check cache first
        if self.cache_client:
            user = await self.cache_client.get(f"user:{user_id}")
            if user:
                return user
        
        # Get from database
        user = await self.db_client.get_user(user_id)
        if not user:
            raise UserNotFoundError(f"User {user_id} not found")
        
        # Update cache
        if self.cache_client:
            await self.cache_client.set(
                f"user:{user_id}",
                user,
                expire=3600
            )
        
        return user
```

### Code Documentation
```python
# examples/documentation.py
from typing import List, Optional

class ModelService:
    """
    Service for interacting with language models.
    
    This service provides a high-level interface for model operations,
    including generation, embedding, and fine-tuning.
    
    Attributes:
        model_name: Name of the model to use
        api_key: API key for model service
        max_tokens: Maximum tokens for generation
    """
    
    def __init__(
        self,
        model_name: str,
        api_key: str,
        max_tokens: Optional[int] = None
    ):
        """
        Initialize the model service.
        
        Args:
            model_name: Name of the model to use
            api_key: API key for authentication
            max_tokens: Maximum tokens for generation (optional)
        """
        self.model_name = model_name
        self.api_key = api_key
        self.max_tokens = max_tokens or 1000
    
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7
    ) -> str:
        """
        Generate text based on prompt.
        
        Args:
            prompt: Input prompt for generation
            temperature: Sampling temperature (default: 0.7)
            
        Returns:
            Generated text
            
        Raises:
            ModelError: If generation fails
        """
        try:
            response = await self.client.generate(
                prompt=prompt,
                temperature=temperature,
                max_tokens=self.max_tokens
            )
            return response.text
        except Exception as e:
            raise ModelError(f"Generation failed: {str(e)}")
```

## CI/CD Pipeline

### GitHub Actions
```yaml
# .github/workflows/ci.yml
name: CI

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
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Run tests
      run: |
        pytest --cov=src tests/
        coverage xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v2

  lint:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install black flake8 mypy
    
    - name: Run linters
      run: |
        black --check src tests
        flake8 src tests
        mypy src
```

### Deployment Pipeline
```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    tags:
      - 'v*'

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v1
    
    - name: Login to Container Registry
      uses: docker/login-action@v1
      with:
        registry: ghcr.io
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}
    
    - name: Build and push
      uses: docker/build-push-action@v2
      with:
        push: true
        tags: |
          ghcr.io/${{ github.repository }}:latest
          ghcr.io/${{ github.repository }}:${{ github.ref_name }}
```

## Testing Guidelines

### Unit Tests
```python
# tests/test_model_service.py
import pytest
from unittest.mock import Mock, patch
from agent360.services.model import ModelService

class TestModelService:
    @pytest.fixture
    def model_service(self):
        return ModelService(
            model_name="gpt-4",
            api_key="test_key"
        )
    
    async def test_generate(self, model_service):
        prompt = "Test prompt"
        expected = "Generated text"
        
        with patch.object(
            model_service.client,
            'generate',
            return_value=Mock(text=expected)
        ):
            result = await model_service.generate(prompt)
            assert result == expected
    
    async def test_generate_error(self, model_service):
        with patch.object(
            model_service.client,
            'generate',
            side_effect=Exception("API Error")
        ):
            with pytest.raises(ModelError):
                await model_service.generate("prompt")
```

### Integration Tests
```python
# tests/integration/test_workflow.py
import pytest
from agent360.workflow import WorkflowManager

class TestWorkflow:
    @pytest.fixture
    async def workflow_manager(self):
        return await WorkflowManager.create()
    
    async def test_complete_workflow(self, workflow_manager):
        workflow_id = await workflow_manager.create_workflow({
            "name": "test_workflow",
            "steps": [
                {"type": "model", "prompt": "test"},
                {"type": "tool", "name": "test_tool"}
            ]
        })
        
        result = await workflow_manager.execute_workflow(workflow_id)
        assert result["status"] == "completed"
```

## Contributing Guidelines

### Pull Request Process
```markdown
## Pull Request Template

### Description
Brief description of the changes

### Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

### How Has This Been Tested?
Describe the tests you ran

### Checklist
- [ ] My code follows the style guidelines
- [ ] I have performed a self-review
- [ ] I have added tests
- [ ] I have updated documentation
```

### Code Review Guidelines
```markdown
## Code Review Checklist

### Functionality
- [ ] Code works as described in the PR
- [ ] Edge cases are handled
- [ ] Error cases are handled

### Code Quality
- [ ] Code follows style guide
- [ ] Code is documented
- [ ] Tests are included
- [ ] No unnecessary complexity

### Security
- [ ] No security vulnerabilities
- [ ] Sensitive data is handled properly
- [ ] Input is validated

### Performance
- [ ] No performance bottlenecks
- [ ] Resource usage is optimized
- [ ] Queries are efficient
```

## Documentation

### API Documentation
```python
# docs/api_docs.py
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

app = FastAPI()

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Agent360 API",
        version="1.0.0",
        description="API documentation for Agent360",
        routes=app.routes,
    )
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
```

### Code Documentation
```python
# docs/code_docs.py
def generate_docs():
    """Generate code documentation using Sphinx."""
    import subprocess
    
    # Generate API documentation
    subprocess.run([
        "sphinx-apidoc",
        "-o",
        "docs/source",
        "src/agent360"
    ])
    
    # Build documentation
    subprocess.run([
        "sphinx-build",
        "-b",
        "html",
        "docs/source",
        "docs/build/html"
    ])
```

## Best Practices

### 1. Code Quality
- Follow PEP 8
- Write tests
- Document code
- Review PRs

### 2. Development Process
- Use feature branches
- Write clear commits
- Update documentation
- Run tests locally

### 3. Security
- Handle secrets properly
- Validate input
- Follow security guidelines
- Regular updates

### 4. Performance
- Profile code
- Optimize queries
- Monitor resources
- Cache appropriately
