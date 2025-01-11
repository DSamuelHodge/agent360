# Agent360 - Enterprise-Grade Agent Infrastructure

## Overview
Agent360 is a scalable, reliable, and observable infrastructure for deploying AI agents in an enterprise environment. It leverages modern technologies including Kubernetes, Temporal, Kong, Redpanda, Cassandra, and Redis.

## Key Components
- Agent Runtime (Model Service, Orchestration Layer, Tools Layer)
- Infrastructure Components (Temporal, Kong, Redpanda, Cassandra, Redis)

## Getting Started

### Prerequisites
- Python 3.9+
- Docker and Docker Compose
- Kubernetes cluster (for production deployment)

### Installation
1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Configuration
1. Copy `.env.example` to `.env`
2. Update environment variables as needed

## Development
- `src/agent_runtime/` - Core agent implementation
- `src/infrastructure/` - Infrastructure components
- `src/tools/` - Tool implementations
- `src/api/` - API endpoints
- `k8s/` - Kubernetes manifests

## Testing
```bash
pytest tests/
```

## Documentation
Refer to the `docs/` directory for detailed documentation:
- Architecture Guide
- API Documentation
- Development Guide
- Operations Manual
