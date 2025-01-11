# Azure Deployment Guide for Agent360

## Overview
This guide outlines the steps to deploy Agent360 on Azure using AKS (Azure Kubernetes Service).

## Prerequisites
- Azure CLI installed and configured
- kubectl installed
- helm installed
- Azure subscription with appropriate permissions

## Infrastructure Setup

### 1. Create Resource Group
```bash
az group create \
  --name agent360-rg \
  --location eastus
```

### 2. Create AKS Cluster
```bash
az aks create \
  --resource-group agent360-rg \
  --name agent360-cluster \
  --node-count 3 \
  --enable-addons monitoring \
  --generate-ssh-keys \
  --node-vm-size Standard_DS2_v2
```

### 3. Get Credentials
```bash
az aks get-credentials \
  --resource-group agent360-rg \
  --name agent360-cluster
```

## Database Setup

### 1. Create Cosmos DB (Cassandra API)
```bash
az cosmosdb create \
  --name agent360-cosmos \
  --resource-group agent360-rg \
  --capabilities EnableCassandra \
  --default-consistency-level Strong

az cosmosdb cassandra keyspace create \
  --account-name agent360-cosmos \
  --name agent360 \
  --resource-group agent360-rg
```

### 2. Create Azure Cache for Redis
```bash
az redis create \
  --name agent360-redis \
  --resource-group agent360-rg \
  --location eastus \
  --sku Premium \
  --vm-size P1
```

## Application Deployment

### 1. Create Azure Container Registry
```bash
az acr create \
  --resource-group agent360-rg \
  --name agent360acr \
  --sku Standard

az acr login --name agent360acr
```

### 2. Configure Secrets
```bash
kubectl create namespace agent360

kubectl create secret generic agent360-secrets \
  --from-literal=cosmos-password=$(az cosmosdb keys list --name agent360-cosmos --resource-group agent360-rg --query primaryMasterKey -o tsv) \
  --from-literal=redis-password=$(az redis list-keys --name agent360-redis --resource-group agent360-rg --query primaryKey -o tsv) \
  --namespace agent360
```

### 3. Deploy Application
```bash
helm upgrade --install agent360 ./helm/agent360 \
  --namespace agent360 \
  --set image.repository=agent360acr.azurecr.io/agent360 \
  --set image.tag=latest \
  --values ./helm/agent360/values-azure.yaml
```

## Networking Setup

### 1. Configure Application Gateway
```bash
az network application-gateway create \
  --name agent360-gateway \
  --resource-group agent360-rg \
  --vnet-name agent360-vnet \
  --subnet agent360-gateway-subnet
```

### 2. Setup HTTPS
```bash
az network application-gateway ssl-cert create \
  --gateway-name agent360-gateway \
  --name agent360-cert \
  --resource-group agent360-rg \
  --cert-file ./certs/agent360.pfx
```

## Monitoring Setup

### 1. Configure Azure Monitor
```bash
az monitor log-analytics workspace create \
  --resource-group agent360-rg \
  --workspace-name agent360-workspace

az aks enable-addons \
  --resource-group agent360-rg \
  --name agent360-cluster \
  --addons monitoring \
  --workspace-resource-id $(az monitor log-analytics workspace show --resource-group agent360-rg --workspace-name agent360-workspace --query id -o tsv)
```

### 2. Setup Application Insights
```bash
az monitor app-insights component create \
  --app agent360-insights \
  --location eastus \
  --resource-group agent360-rg
```

## Backup Configuration

### 1. Create Storage Account
```bash
az storage account create \
  --name agent360storage \
  --resource-group agent360-rg \
  --sku Standard_LRS

az storage container create \
  --name backups \
  --account-name agent360storage
```

### 2. Configure Backup Policy
```bash
az backup vault create \
  --name agent360-vault \
  --resource-group agent360-rg \
  --location eastus

az backup protection enable-for-vm \
  --resource-group agent360-rg \
  --vault-name agent360-vault \
  --vm $(az vm show -g agent360-rg -n agent360-vm --query id -o tsv) \
  --policy-name DefaultPolicy
```

## Security Configuration

### 1. Configure Network Security
```bash
az network nsg create \
  --resource-group agent360-rg \
  --name agent360-nsg

az network nsg rule create \
  --resource-group agent360-rg \
  --nsg-name agent360-nsg \
  --name allow-https \
  --protocol tcp \
  --priority 100 \
  --destination-port-range 443
```

### 2. Enable Azure WAF
```bash
az network application-gateway waf-config set \
  --gateway-name agent360-gateway \
  --resource-group agent360-rg \
  --enabled true \
  --firewall-mode Prevention \
  --rule-set-version 3.0
```

## Scaling Configuration

### 1. Configure Autoscaling
```bash
kubectl autoscale deployment agent360 \
  --namespace agent360 \
  --min=3 \
  --max=10 \
  --cpu-percent=80
```

### 2. Configure AKS Cluster Autoscaler
```bash
az aks update \
  --resource-group agent360-rg \
  --name agent360-cluster \
  --enable-cluster-autoscaler \
  --min-count 1 \
  --max-count 5
```

## Maintenance

### Health Monitoring
```bash
# Check AKS health
az aks show \
  --resource-group agent360-rg \
  --name agent360-cluster \
  --query 'provisioningState'

# Check pod health
kubectl get pods -n agent360

# View logs
az monitor log-analytics query \
  --workspace $(az monitor log-analytics workspace show --resource-group agent360-rg --workspace-name agent360-workspace --query id -o tsv) \
  --query 'ContainerLog | where ContainerName == "agent360"'
```

### Updates and Patches
```bash
# Update AKS
az aks upgrade \
  --resource-group agent360-rg \
  --name agent360-cluster \
  --kubernetes-version 1.25.0

# Update application
az acr build --registry agent360acr --image agent360:latest .
helm upgrade agent360 ./helm/agent360 --namespace agent360
```

## Disaster Recovery

### 1. Configure Geo-Replication
```bash
# Enable Cosmos DB geo-replication
az cosmosdb update \
  --name agent360-cosmos \
  --resource-group agent360-rg \
  --locations regionName=eastus failoverPriority=0 isZoneRedundant=true \
  --locations regionName=westus failoverPriority=1 isZoneRedundant=true

# Enable Redis geo-replication
az redis update \
  --name agent360-redis \
  --resource-group agent360-rg \
  --enable-geo-replication true
```

### 2. Configure Backup and Restore
```bash
# Create backup
az backup protection backup-now \
  --resource-group agent360-rg \
  --vault-name agent360-vault \
  --item-name agent360-vm \
  --retain-until 30

# Restore from backup
az backup protection restore-disks \
  --resource-group agent360-rg \
  --vault-name agent360-vault \
  --recovery-point-id $RECOVERY_POINT \
  --storage-account agent360storage
```

## Troubleshooting

### Common Issues

1. Pod Startup Issues
```bash
kubectl describe pod <pod-name> -n agent360
kubectl logs <pod-name> -n agent360
```

2. Network Issues
```bash
az network watcher test-ip-flow \
  --resource-group agent360-rg \
  --vm agent360-vm \
  --direction inbound \
  --protocol tcp \
  --local 10.0.0.4:443 \
  --remote 192.168.1.1:1234
```

3. Performance Issues
```bash
az monitor metrics list \
  --resource $(az aks show -g agent360-rg -n agent360-cluster --query id -o tsv) \
  --metric CPUUsagePercentage
```

### Support Resources
- Azure Documentation: https://docs.microsoft.com/azure/
- AKS Documentation: https://docs.microsoft.com/azure/aks/
- Agent360 Support: support@agent360.example.com
