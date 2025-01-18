#!/bin/bash

# Build and push Docker images
docker-compose build
docker-compose push

# Apply Kubernetes configurations
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/network-policies.yaml

# Install Helm chart
helm upgrade --install agent360 ./helm/agent360 \
  --namespace agent360 \
  --values helm/agent360/values.yaml \
  --wait

# Deploy monitoring
kubectl apply -f monitoring/grafana/ -n agent360