# Agent360 Infrastructure Deployment Guide

This guide provides step-by-step instructions for deploying the Agent360 infrastructure on Kubernetes.

## Prerequisites

- Kubernetes cluster (v1.20+)
- Helm v3.0+
- kubectl configured with cluster access
- Access to container registry (ghcr.io)
- Domain name for ingress configuration
- SSL certificate or cert-manager installed

## Pre-deployment Setup

1. **Create Namespace**
   ```bash
   kubectl create namespace agent360
   ```

2. **Configure Container Registry Access**
   ```bash
   kubectl create secret docker-registry ghcr-secret \
     --namespace agent360 \
     --docker-server=ghcr.io \
     --docker-username=<your-username> \
     --docker-password=<your-pat> \
     --docker-email=<your-email>
   ```

3. **Add Required Helm Repositories**
   ```bash
   helm repo add bitnami https://charts.bitnami.com/bitnami
   helm repo add redpanda https://charts.redpanda.com/
   helm repo add temporal https://temporal.github.io/helm-charts
   helm repo update
   ```

## Environment Variables and Secrets Setup

### Pre-deployment Requirements

Before deploying Agent360, you need to set up the following environment variables and secrets:

1. **Create Kubernetes Secrets**
   ```bash
   # Create a secret for database credentials
   kubectl create secret generic db-credentials \
     --namespace agent360 \
     --from-literal=CASSANDRA_USER=<your-cassandra-user> \
     --from-literal=CASSANDRA_PASSWORD=<your-cassandra-password>

   # Create a secret for Redis credentials
   kubectl create secret generic redis-credentials \
     --namespace agent360 \
     --from-literal=REDIS_PASSWORD=<your-redis-password>

   # Create a secret for Temporal credentials
   kubectl create secret generic temporal-credentials \
     --namespace agent360 \
     --from-literal=TEMPORAL_USER=<your-temporal-user> \
     --from-literal=TEMPORAL_PASSWORD=<your-temporal-password>
   ```

2. **Configure TLS Certificates**
   ```bash
   # If using cert-manager
   kubectl apply -f - <<EOF
   apiVersion: cert-manager.io/v1
   kind: Certificate
   metadata:
     name: agent360-tls
     namespace: agent360
   spec:
     secretName: agent360-tls
     issuerRef:
       name: letsencrypt-prod
       kind: ClusterIssuer
     dnsNames:
     - agent360.example.com
   EOF
   ```

3. **Update Helm Values**
   Create a `custom-values.yaml` file with your environment-specific values:
   ```yaml
   environment: production
   
   api:
     env:
       - name: CASSANDRA_USER
         valueFrom:
           secretKeyRef:
             name: db-credentials
             key: CASSANDRA_USER
       - name: CASSANDRA_PASSWORD
         valueFrom:
           secretKeyRef:
             name: db-credentials
             key: CASSANDRA_PASSWORD
       - name: REDIS_PASSWORD
         valueFrom:
           secretKeyRef:
             name: redis-credentials
             key: REDIS_PASSWORD
       - name: TEMPORAL_USER
         valueFrom:
           secretKeyRef:
             name: temporal-credentials
             key: TEMPORAL_USER
       - name: TEMPORAL_PASSWORD
         valueFrom:
           secretKeyRef:
             name: temporal-credentials
             key: TEMPORAL_PASSWORD

   ingress:
     hosts:
       - host: your-domain.com
         paths:
           - path: /
             pathType: Prefix
   ```

### Order of Operations

1. **Before Deployment**:
   - Set up all required secrets in Kubernetes
   - Configure TLS certificates
   - Update custom values file with environment-specific settings
   - Configure container registry access

2. **During Deployment**:
   - The Helm chart will automatically use the configured secrets
   - Environment variables will be injected into the pods
   - TLS certificates will be mounted where needed

3. **Post Deployment**:
   - Verify secrets are properly mounted
   - Check environment variables are correctly set
   - Validate TLS certificate configuration

### Security Best Practices

- Never commit secrets to version control
- Rotate secrets regularly
- Use separate secrets for different environments
- Implement proper RBAC policies
- Monitor secret usage and access

## Deployment Steps

1. **Configure Values**
   - Copy the default values file:
     ```bash
     cp helm/agent360/values.yaml my-values.yaml
     ```
   - Edit `my-values.yaml` to set:
     - Your domain in `ingress.hosts`
     - Proper image repository and tag
     - Resource limits and requests
     - Environment-specific configurations

2. **Deploy Dependencies**
   The main Helm chart will automatically install dependencies:
   - Redis
   - Cassandra
   - Redpanda
   - Temporal
   - Kong

3. **Deploy Agent360**
   ```bash
   helm install agent360 ./helm/agent360 \
     --namespace agent360 \
     --values my-values.yaml \
     --wait
   ```

4. **Apply Network Policies**
   ```bash
   kubectl apply -f k8s/network-policies.yaml -n agent360
   ```

## Post-deployment Verification

1. **Check Pod Status**
   ```bash
   kubectl get pods -n agent360
   ```

2. **Verify Services**
   ```bash
   kubectl get services -n agent360
   ```

3. **Test Ingress**
   ```bash
   kubectl get ingress -n agent360
   ```

4. **Verify Dependencies**
   ```bash
   helm list -n agent360
   ```

## Monitoring Setup

1. **Deploy Monitoring Stack**
   ```bash
   kubectl apply -f monitoring/grafana/ -n agent360
   ```

2. **Access Grafana**
   - Get the Grafana service URL:
     ```bash
     kubectl get svc -n agent360 | grep grafana
     ```
   - Default credentials are in the values.yaml file

## Troubleshooting

1. **Check Pod Logs**
   ```bash
   kubectl logs -f <pod-name> -n agent360
   ```

2. **Check Events**
   ```bash
   kubectl get events -n agent360
   ```

3. **Common Issues**
   - If pods are pending: Check resource quotas and node capacity
   - If services are not accessible: Verify network policies
   - If ingress fails: Check DNS configuration and TLS settings

## Scaling and Maintenance

1. **Scaling Services**
   ```bash
   kubectl scale deployment <deployment-name> --replicas=<number> -n agent360
   ```

2. **Updating the Application**
   ```bash
   helm upgrade agent360 ./helm/agent360 \
     --namespace agent360 \
     --values my-values.yaml \
     --wait
   ```

3. **Backup Considerations**
   - Regular backups of Cassandra data
   - Backup of Redis if persistence is enabled
   - Export of Grafana dashboards

## Security Notes

- Ensure all secrets are properly managed
- Regularly rotate service accounts and credentials
- Keep network policies updated
- Monitor security advisories for dependencies

## Support

For additional support:
- Check the documentation in `/docs`
- Review logs in Grafana dashboards
- Contact the infrastructure team

Remember to always test deployments in a staging environment first before applying to production.
