# GCP Deployment Guide for Agent360

## Overview
This guide outlines the steps to deploy Agent360 on Google Cloud Platform (GCP) using GKE (Google Kubernetes Engine).

## Prerequisites
- gcloud CLI installed and configured
- kubectl installed
- helm installed
- GCP project with appropriate permissions

## Infrastructure Setup

### 1. Set Project and Zone
```bash
export PROJECT_ID=agent360-project
export COMPUTE_ZONE=us-central1-a

gcloud config set project $PROJECT_ID
gcloud config set compute/zone $COMPUTE_ZONE
```

### 2. Create GKE Cluster
```bash
gcloud container clusters create agent360-cluster \
  --num-nodes=3 \
  --machine-type=e2-standard-2 \
  --enable-autoscaling \
  --min-nodes=1 \
  --max-nodes=5 \
  --enable-autorepair \
  --enable-ip-alias
```

### 3. Get Credentials
```bash
gcloud container clusters get-credentials agent360-cluster
```

## Database Setup

### 1. Create Cloud Spanner Instance
```bash
gcloud spanner instances create agent360-spanner \
  --config=regional-us-central1 \
  --description="Agent360 Database" \
  --nodes=1

gcloud spanner databases create agent360 \
  --instance=agent360-spanner
```

### 2. Create Memorystore Instance
```bash
gcloud redis instances create agent360-redis \
  --size=5 \
  --region=us-central1 \
  --redis-version=redis_6_x
```

## Application Deployment

### 1. Create Container Registry
```bash
gcloud artifacts repositories create agent360-repo \
  --repository-format=docker \
  --location=us-central1
```

### 2. Configure Secrets
```bash
kubectl create namespace agent360

kubectl create secret generic agent360-secrets \
  --from-literal=spanner-credentials="$(cat spanner-key.json)" \
  --from-literal=redis-password="$(gcloud redis instances get-auth-string agent360-redis)" \
  --namespace agent360
```

### 3. Deploy Application
```bash
helm upgrade --install agent360 ./helm/agent360 \
  --namespace agent360 \
  --set image.repository=us-central1-docker.pkg.dev/$PROJECT_ID/agent360-repo/agent360 \
  --set image.tag=latest \
  --values ./helm/agent360/values-gcp.yaml
```

## Network Setup

### 1. Configure Load Balancer
```bash
gcloud compute addresses create agent360-ip \
  --global

kubectl apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: agent360-ingress
  annotations:
    kubernetes.io/ingress.global-static-ip-name: agent360-ip
spec:
  rules:
  - host: agent360.example.com
    http:
      paths:
      - path: /*
        pathType: ImplementationSpecific
        backend:
          service:
            name: agent360
            port:
              number: 80
EOF
```

### 2. Configure SSL
```bash
gcloud compute ssl-certificates create agent360-cert \
  --domains=agent360.example.com
```

## Monitoring Setup

### 1. Configure Cloud Monitoring
```bash
gcloud monitoring dashboards create \
  --config-from-file=monitoring/dashboards/agent360.json

gcloud monitoring channels create \
  --display-name="Agent360 Alerts" \
  --type=email \
  --email-address=alerts@agent360.example.com
```

### 2. Setup Cloud Trace
```bash
gcloud services enable cloudtrace.googleapis.com

kubectl apply -f - <<EOF
apiVersion: opentelemetry.io/v1alpha1
kind: OpenTelemetryCollector
metadata:
  name: agent360-collector
spec:
  config: |
    receivers:
      otlp:
        protocols:
          grpc:
          http:
    exporters:
      googlecloud:
        project: $PROJECT_ID
    service:
      pipelines:
        traces:
          receivers: [otlp]
          exporters: [googlecloud]
EOF
```

## Backup Configuration

### 1. Configure Cloud Storage
```bash
gsutil mb -l us-central1 gs://agent360-backups

gsutil lifecycle set backup-lifecycle.json gs://agent360-backups
```

### 2. Setup Backup Jobs
```bash
kubectl apply -f k8s/gcp/backup-cronjob.yaml
```

## Security Configuration

### 1. Configure IAM
```bash
# Create service account
gcloud iam service-accounts create agent360-sa \
  --display-name="Agent360 Service Account"

# Grant permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:agent360-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/spanner.databaseUser"
```

### 2. Enable Cloud Armor
```bash
gcloud compute security-policies create agent360-policy \
  --description="Agent360 WAF policy"

gcloud compute security-policies rules create 1000 \
  --security-policy=agent360-policy \
  --expression="evaluatePreconfiguredExpr('xss-stable')" \
  --action=deny-403
```

## Scaling Configuration

### 1. Configure HPA
```bash
kubectl autoscale deployment agent360 \
  --namespace agent360 \
  --min=3 \
  --max=10 \
  --cpu-percent=80
```

### 2. Configure GKE Cluster Autoscaler
```bash
gcloud container clusters update agent360-cluster \
  --enable-autoscaling \
  --min-nodes=1 \
  --max-nodes=5
```

## Maintenance

### Health Monitoring
```bash
# Check GKE health
gcloud container clusters describe agent360-cluster \
  --format="table(status,currentNodeCount,currentMasterVersion)"

# Check pod health
kubectl get pods -n agent360

# View logs
gcloud logging read "resource.type=k8s_container AND resource.labels.namespace_name=agent360" \
  --format="table(timestamp,textPayload)"
```

### Updates and Patches
```bash
# Update GKE
gcloud container clusters upgrade agent360-cluster \
  --master --cluster-version=latest

# Update application
gcloud builds submit --tag us-central1-docker.pkg.dev/$PROJECT_ID/agent360-repo/agent360:latest
helm upgrade agent360 ./helm/agent360 --namespace agent360
```

## Disaster Recovery

### 1. Configure Cross-Region Replication
```bash
# Enable Spanner multi-region
gcloud spanner instances update agent360-spanner \
  --configuration=nam3 \
  --nodes=3

# Enable GCS replication
gsutil rewrite -r -s STANDARD gs://agent360-backups/**
```

### 2. Configure Backup and Restore
```bash
# Create backup
gcloud spanner backups create backup-$(date +%Y%m%d) \
  --instance=agent360-spanner \
  --database=agent360 \
  --expiration-date=$(date -d "+7 days" +%Y-%m-%d)

# Restore from backup
gcloud spanner databases restore agent360-restore \
  --instance=agent360-spanner \
  --backup=backup-20250111
```

## Troubleshooting

### Common Issues

1. Pod Issues
```bash
kubectl describe pod <pod-name> -n agent360
kubectl logs <pod-name> -n agent360
```

2. Network Issues
```bash
gcloud compute firewall-rules list
gcloud compute routes list
```

3. Performance Issues
```bash
gcloud monitoring metrics list \
  --filter="metric.type = starts_with(\"kubernetes.io/\")"
```

### Support Resources
- GCP Documentation: https://cloud.google.com/docs
- GKE Documentation: https://cloud.google.com/kubernetes-engine/docs
- Agent360 Support: support@agent360.example.com
