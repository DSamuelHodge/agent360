# AWS Deployment Guide for Agent360

## Overview
This guide outlines the steps to deploy Agent360 on AWS using EKS (Elastic Kubernetes Service).

## Prerequisites
- AWS CLI configured with appropriate permissions
- kubectl installed
- helm installed
- eksctl installed

## Infrastructure Setup

### 1. Create EKS Cluster
```bash
eksctl create cluster \
  --name agent360-cluster \
  --region us-west-2 \
  --nodegroup-name standard-workers \
  --node-type t3.large \
  --nodes 3 \
  --nodes-min 1 \
  --nodes-max 4 \
  --managed
```

### 2. Configure IAM Roles
```bash
eksctl create iamserviceaccount \
  --name agent360-service-account \
  --namespace agent360 \
  --cluster agent360-cluster \
  --attach-policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess \
  --approve
```

## Database Setup

### 1. Create Cassandra Cluster (Amazon Keyspaces)
```bash
aws keyspaces create-keyspace --keyspace-name agent360

aws keyspaces create-table \
  --keyspace-name agent360 \
  --table-name users \
  --schema-definition file://schemas/users.json
```

### 2. Configure Redis (ElastiCache)
```bash
aws elasticache create-replication-group \
  --replication-group-id agent360-redis \
  --replication-group-description "Agent360 Redis cluster" \
  --engine redis \
  --cache-node-type cache.t3.medium \
  --num-cache-clusters 2
```

## Application Deployment

### 1. Configure Secrets
```bash
kubectl create namespace agent360

kubectl create secret generic agent360-secrets \
  --from-literal=cassandra-password=$CASSANDRA_PASSWORD \
  --from-literal=redis-password=$REDIS_PASSWORD \
  --from-literal=jwt-secret=$JWT_SECRET \
  --namespace agent360
```

### 2. Deploy Application
```bash
helm upgrade --install agent360 ./helm/agent360 \
  --namespace agent360 \
  --set image.tag=latest \
  --set environment=production \
  --values ./helm/agent360/values-aws.yaml
```

### 3. Configure Ingress (ALB)
```bash
kubectl apply -f k8s/aws/ingress.yaml
```

## Monitoring Setup

### 1. Deploy Prometheus
```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace
```

### 2. Configure CloudWatch
```bash
kubectl apply -f k8s/aws/cloudwatch-agent.yaml
```

## Backup Configuration

### 1. Configure S3 Bucket
```bash
aws s3api create-bucket \
  --bucket agent360-backups \
  --region us-west-2 \
  --create-bucket-configuration LocationConstraint=us-west-2
```

### 2. Setup Backup Jobs
```bash
kubectl apply -f k8s/aws/backup-cronjob.yaml
```

## Security Configuration

### 1. Configure Security Groups
```bash
aws ec2 create-security-group \
  --group-name agent360-sg \
  --description "Security group for Agent360"

aws ec2 authorize-security-group-ingress \
  --group-name agent360-sg \
  --protocol tcp \
  --port 443 \
  --cidr 0.0.0.0/0
```

### 2. Enable WAF
```bash
aws wafv2 create-web-acl \
  --name agent360-waf \
  --scope REGIONAL \
  --default-action Block={} \
  --rules file://waf-rules.json
```

## Scaling Configuration

### 1. Configure HPA
```bash
kubectl apply -f k8s/aws/hpa.yaml
```

### 2. Configure Cluster Autoscaler
```bash
helm install cluster-autoscaler autoscaler/cluster-autoscaler \
  --namespace kube-system \
  --set autoDiscovery.clusterName=agent360-cluster
```

## Maintenance

### Health Checks
```bash
# Check pod health
kubectl get pods -n agent360

# Check service health
kubectl get services -n agent360

# Check logs
kubectl logs -f deployment/agent360 -n agent360
```

### Updating
```bash
# Update application
helm upgrade agent360 ./helm/agent360 \
  --namespace agent360 \
  --set image.tag=new-version

# Update dependencies
helm dependency update ./helm/agent360
```

### Rollback
```bash
# List revisions
helm history agent360 -n agent360

# Rollback to previous version
helm rollback agent360 1 -n agent360
```

## Troubleshooting

### Common Issues

1. Pod Startup Failures
```bash
kubectl describe pod <pod-name> -n agent360
kubectl logs <pod-name> -n agent360
```

2. Database Connection Issues
```bash
kubectl exec -it <pod-name> -n agent360 -- nc -zv cassandra 9042
kubectl exec -it <pod-name> -n agent360 -- nc -zv redis 6379
```

3. Performance Issues
```bash
kubectl top pods -n agent360
kubectl top nodes
```

### Support Resources
- AWS EKS Documentation: https://docs.aws.amazon.com/eks/
- Kubernetes Documentation: https://kubernetes.io/docs/
- Agent360 Support: support@agent360.example.com
