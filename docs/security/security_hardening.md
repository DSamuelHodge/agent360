# Agent360 Security Hardening Guide

## Overview
This guide provides comprehensive security hardening measures for Agent360.

## Table of Contents
1. [Infrastructure Security](#infrastructure-security)
2. [Application Security](#application-security)
3. [Data Security](#data-security)
4. [Network Security](#network-security)
5. [Access Control](#access-control)
6. [Monitoring and Auditing](#monitoring-and-auditing)
7. [Incident Response](#incident-response)

## Infrastructure Security

### Container Security
```yaml
# security-context.yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  readOnlyRootFilesystem: true
  allowPrivilegeEscalation: false
  capabilities:
    drop:
      - ALL
```

### Pod Security
```yaml
# pod-security-policy.yaml
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: agent360-psp
spec:
  privileged: false
  seLinux:
    rule: RunAsAny
  runAsUser:
    rule: MustRunAsNonRoot
  fsGroup:
    rule: RunAsAny
  volumes:
    - configMap
    - secret
    - emptyDir
```

### Node Security
```bash
# Harden node configuration
cat << EOF > /etc/sysctl.d/99-kubernetes-hardening.conf
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
EOF

sysctl --system
```

## Application Security

### API Security
```python
# security.py
from fastapi import Security, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except:
        raise HTTPException(status_code=401, detail="Invalid token")
```

### Input Validation
```python
# validation.py
from pydantic import BaseModel, validator

class AgentRequest(BaseModel):
    query: str
    tools: List[str]
    
    @validator('query')
    def validate_query(cls, v):
        if len(v) > 1000:
            raise ValueError("Query too long")
        return v
    
    @validator('tools')
    def validate_tools(cls, v):
        allowed_tools = ["rest_tool", "database_tool"]
        if not all(tool in allowed_tools for tool in v):
            raise ValueError("Invalid tools requested")
        return v
```

### Dependency Security
```yaml
# requirements.txt
cryptography>=3.4.7
pyjwt>=2.1.0
bcrypt>=3.2.0
```

## Data Security

### Encryption at Rest
```python
# encryption.py
from cryptography.fernet import Fernet

class DataEncryption:
    def __init__(self, key: bytes):
        self.fernet = Fernet(key)
    
    def encrypt(self, data: bytes) -> bytes:
        return self.fernet.encrypt(data)
    
    def decrypt(self, data: bytes) -> bytes:
        return self.fernet.decrypt(data)
```

### Data Masking
```python
# masking.py
import re

class DataMasker:
    @staticmethod
    def mask_pii(text: str) -> str:
        # Mask email addresses
        text = re.sub(
            r'[\w\.-]+@[\w\.-]+\.\w+',
            '[EMAIL REDACTED]',
            text
        )
        
        # Mask phone numbers
        text = re.sub(
            r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            '[PHONE REDACTED]',
            text
        )
        
        return text
```

### Secure Configuration
```yaml
# secure-config.yaml
apiVersion: v1
kind: Secret
metadata:
  name: agent360-secrets
type: Opaque
data:
  database-password: <base64-encoded>
  api-key: <base64-encoded>
  encryption-key: <base64-encoded>
```

## Network Security

### Network Policies
```yaml
# network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: agent360-network-policy
spec:
  podSelector:
    matchLabels:
      app: agent360
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: database
    ports:
    - protocol: TCP
      port: 5432
```

### TLS Configuration
```python
# tls_config.py
ssl_context = ssl.create_default_context()
ssl_context.minimum_version = ssl.TLSVersion.TLSv1_3
ssl_context.set_ciphers('ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384')
```

### Service Mesh
```yaml
# istio-config.yaml
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: agent360-peer-auth
spec:
  selector:
    matchLabels:
      app: agent360
  mtls:
    mode: STRICT
```

## Access Control

### RBAC Configuration
```yaml
# rbac.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: agent360-role
rules:
- apiGroups: [""]
  resources: ["pods", "services"]
  verbs: ["get", "list"]
```

### Authentication
```python
# auth.py
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthManager:
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        return pwd_context.hash(password)
```

### Authorization
```python
# authorization.py
from enum import Enum
from typing import List

class Permission(Enum):
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"

class AuthorizationManager:
    def check_permission(self, user_id: str, required_permission: Permission) -> bool:
        user_permissions = self.get_user_permissions(user_id)
        return required_permission in user_permissions
```

## Monitoring and Auditing

### Security Monitoring
```python
# security_monitoring.py
import logging
from datetime import datetime

class SecurityMonitor:
    def __init__(self):
        self.logger = logging.getLogger("security")
    
    def log_security_event(self, event_type: str, details: dict):
        self.logger.warning(
            "Security event: %s, Details: %s",
            event_type,
            details
        )
```

### Audit Logging
```python
# audit.py
class AuditLogger:
    def log_action(
        self,
        user_id: str,
        action: str,
        resource: str,
        status: str
    ):
        audit_entry = {
            "timestamp": datetime.utcnow(),
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "status": status,
            "ip_address": request.client.host
        }
        self.store_audit_log(audit_entry)
```

### Metrics Collection
```python
# metrics.py
from prometheus_client import Counter, Histogram

security_events = Counter(
    'agent360_security_events_total',
    'Total security events',
    ['event_type', 'severity']
)

auth_latency = Histogram(
    'agent360_auth_latency_seconds',
    'Authentication latency'
)
```

## Incident Response

### Alert Configuration
```yaml
# alerts.yaml
groups:
- name: SecurityAlerts
  rules:
  - alert: HighFailedLogins
    expr: rate(agent360_failed_logins_total[5m]) > 10
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: High rate of failed login attempts
```

### Response Procedures
```python
# incident_response.py
class IncidentResponder:
    async def handle_security_incident(self, incident_type: str, details: dict):
        # Log incident
        self.log_incident(incident_type, details)
        
        # Take immediate action
        await self.immediate_response(incident_type)
        
        # Notify security team
        await self.notify_security_team(incident_type, details)
```

### Recovery Procedures
```python
# recovery.py
class SecurityRecovery:
    async def recover_from_incident(self, incident_id: str):
        # Get incident details
        incident = await self.get_incident(incident_id)
        
        # Execute recovery steps
        await self.execute_recovery_plan(incident)
        
        # Verify recovery
        await self.verify_system_security()
```

## Best Practices

### 1. Regular Security Updates
```bash
# Update security packages
apt-get update
apt-get upgrade -y

# Update container images
docker pull agent360:latest
```

### 2. Security Scanning
```bash
# Scan container
trivy image agent360:latest

# Scan dependencies
safety check

# Scan code
bandit -r src/
```

### 3. Backup Security
```bash
# Encrypt backups
gpg --encrypt --recipient security@agent360.com backup.tar

# Verify backup integrity
sha256sum backup.tar.gpg > backup.checksum
```

### 4. Documentation
- Keep security procedures updated
- Document incident responses
- Maintain security contacts
- Update security policies
