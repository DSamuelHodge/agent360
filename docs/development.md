# Agent360 Development Guide

## Development Environment Setup

### Prerequisites
1. Python 3.9+
2. Docker and Docker Compose
3. Kubernetes cluster (minikube for local development)
4. Helm

### Local Setup

1. Clone the repository:
```bash
git clone https://github.com/your-org/agent360.git
cd agent360
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

4. Start local infrastructure:
```bash
docker-compose up -d
```

### Development Workflow

#### 1. Code Style
- Use Black for code formatting
- Follow PEP 8 guidelines
- Use type hints
- Write docstrings in Google format

#### 2. Testing
- Write unit tests for new features
- Include integration tests
- Run tests locally:
```bash
pytest tests/
```

#### 3. Git Workflow
1. Create feature branch
2. Make changes
3. Run tests and linting
4. Submit pull request
5. Address review comments

### Tool Development

#### Creating New Tools
1. Inherit from BaseTool
2. Implement execute method
3. Add metrics collection
4. Include error handling
5. Write tests

Example:
```python
from src.tools.base import BaseTool, ToolMetadata

class CustomTool(BaseTool):
    def __init__(self):
        metadata = ToolMetadata(
            name="custom_tool",
            description="Custom tool description",
            version="1.0.0",
            author="Your Name",
            parameters={
                "param1": "Parameter description"
            }
        )
        super().__init__(metadata)
        
    async def execute(self, parameters):
        # Implementation
        pass
```

### Deployment

#### Local Kubernetes
1. Start minikube:
```bash
minikube start
```

2. Install Helm chart:
```bash
helm install agent360 ./helm/agent360 -f values.local.yaml
```

#### Production
1. Update values.yaml
2. Deploy via CI/CD pipeline
3. Monitor deployment
4. Verify health checks

### Monitoring

#### Local Monitoring
1. Access Prometheus:
```bash
kubectl port-forward svc/prometheus-server 9090:9090
```

2. Access Grafana:
```bash
kubectl port-forward svc/grafana 3000:3000
```

### Troubleshooting

#### Common Issues
1. Connection Issues
   - Check network policies
   - Verify service discovery
   - Check DNS resolution

2. Performance Issues
   - Monitor resource usage
   - Check connection pools
   - Analyze traces

3. Authentication Issues
   - Verify token validity
   - Check RBAC settings
   - Review audit logs
