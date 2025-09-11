# 📦 Installation Guide

Complete installation guide for the Trading System covering all deployment options and configurations.

## 🎯 Installation Options

### Quick Reference

| Method | Difficulty | Use Case | Time |
|--------|------------|----------|------|
| **Docker** | ⭐⭐ | Development/Production | 5-10 min |
| **Local Python** | ⭐⭐⭐ | Development | 15-20 min |
| **Kubernetes** | ⭐⭐⭐⭐ | Production | 30-60 min |
| **AWS/Azure** | ⭐⭐⭐⭐⭐ | Enterprise | 60+ min |

## 🐳 Docker Installation (Recommended)

### Prerequisites

- **Docker**: 20.10 or higher
- **Docker Compose**: 2.0 or higher
- **Git**: For cloning repository
- **4GB RAM** minimum, 8GB recommended

### Step-by-Step Installation

#### 1. Clone Repository

```bash
git clone https://github.com/your-org/trading-system.git
cd trading-system
```

#### 2. Choose Environment

```bash
# For development (includes all services)
cp docker/docker-compose.dev.yml docker-compose.yml

# For production (optimized for performance)
cp docker/docker-compose.prod.yml docker-compose.yml
```

#### 3. Configure Environment Variables

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

Basic `.env` configuration:

```bash
# Application Environment
TRADING_ENV=development

# Database Configuration
DATABASE_PATH=data/financial_data.duckdb
DATABASE_MEMORY=false

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_SECRET_KEY=your-development-secret-key

# Dashboard Configuration
DASHBOARD_HOST=0.0.0.0
DASHBOARD_PORT=8080

# WebSocket Configuration
WEBSOCKET_HOST=0.0.0.0
WEBSOCKET_PORT=8081
```

#### 4. Start Services

```bash
# Start all services
docker-compose up -d

# Start with build (first time)
docker-compose up -d --build

# View startup logs
docker-compose logs -f
```

#### 5. Verify Installation

```bash
# Check service status
docker-compose ps

# Test API health
curl http://localhost:8000/health

# Test dashboard
curl http://localhost:8080/

# Expected API response:
{
  "status": "healthy",
  "timestamp": "2024-09-05T10:30:00Z",
  "version": "2.0.0",
  "service": "trading_system_api"
}
```

### Docker Troubleshooting

#### Common Issues

**Port Already in Use**
```bash
# Find process using port
lsof -i :8000

# Kill process
kill -9 <PID>

# Or change ports in docker-compose.yml
ports:
  - "8001:8000"  # Change host port
```

**Permission Denied**
```bash
# Fix Docker permissions
sudo usermod -aG docker $USER
newgrp docker
```

**Out of Memory**
```bash
# Increase Docker memory limit
# Docker Desktop: Settings → Resources → Memory
# Or limit container memory
docker-compose.yml:
services:
  api:
    deploy:
      resources:
        limits:
          memory: 1G
```

## 🐍 Local Python Installation

### Prerequisites

- **Python**: 3.11 or higher
- **pip**: Latest version
- **Git**: For cloning repository
- **4GB RAM** minimum

### System Dependencies

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-dev
sudo apt install -y build-essential libssl-dev libffi-dev
```

#### macOS
```bash
# Install Homebrew if not installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python
brew install python@3.11
```

#### Windows
```powershell
# Download Python from python.org
# Or use Chocolatey
choco install python --version=3.11.0
```

### Step-by-Step Installation

#### 1. Clone Repository

```bash
git clone https://github.com/your-org/trading-system.git
cd trading-system
```

#### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Linux/macOS
source venv/bin/activate

# Windows
venv\Scripts\activate
```

#### 3. Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Optional: Install development dependencies
pip install -r requirements-dev.txt
```

#### 4. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

#### 5. Initialize Database

```bash
# Create data directory
mkdir -p data

# Run database migrations
python scripts/setup.py
```

#### 6. Start Services

```bash
# Start API server
python -m src.interfaces.api.main

# In another terminal, start dashboard
python -m src.interfaces.dashboard.main

# In another terminal, start WebSocket server
python -m src.interfaces.websocket.main
```

#### 7. Verify Installation

```bash
# Test API
curl http://localhost:8000/health

# Test CLI
python -m src.interfaces.cli.main --help

# Run tests
python -m pytest tests/unit/ -v
```

## ☸️ Kubernetes Installation

### Prerequisites

- **Kubernetes**: 1.24 or higher
- **kubectl**: Configured for your cluster
- **Helm**: 3.0 or higher
- **Docker Registry**: For storing images

### Step-by-Step Installation

#### 1. Build and Push Images

```bash
# Build Docker images
docker build -t your-registry/trading-api:latest -f docker/Dockerfile.api .
docker build -t your-registry/trading-dashboard:latest -f docker/Dockerfile.dashboard .
docker build -t your-registry/trading-websocket:latest -f docker/Dockerfile.websocket .

# Push to registry
docker push your-registry/trading-api:latest
docker push your-registry/trading-dashboard:latest
docker push your-registry/trading-websocket:latest
```

#### 2. Create Namespace

```bash
kubectl create namespace trading-system
```

#### 3. Configure Secrets

```yaml
# k8s/secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: trading-secrets
  namespace: trading-system
type: Opaque
data:
  api-secret-key: <base64-encoded-secret>
  db-password: <base64-encoded-password>
  redis-password: <base64-encoded-password>
```

```bash
kubectl apply -f k8s/secrets.yaml
```

#### 4. Configure ConfigMap

```yaml
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: trading-config
  namespace: trading-system
data:
  TRADING_ENV: "production"
  DATABASE_URL: "postgresql://trading:password@db:5432/trading"
  REDIS_URL: "redis://redis:6379"
  API_HOST: "0.0.0.0"
  API_PORT: "8000"
```

```bash
kubectl apply -f k8s/configmap.yaml
```

#### 5. Deploy Database

```bash
# Deploy PostgreSQL
kubectl apply -f k8s/postgres-deployment.yaml

# Wait for database to be ready
kubectl wait --for=condition=ready pod -l app=postgres -n trading-system
```

#### 6. Deploy Redis

```bash
kubectl apply -f k8s/redis-deployment.yaml
```

#### 7. Deploy Application

```bash
# Deploy API
kubectl apply -f k8s/api-deployment.yaml

# Deploy Dashboard
kubectl apply -f k8s/dashboard-deployment.yaml

# Deploy WebSocket
kubectl apply -f k8s/websocket-deployment.yaml
```

#### 8. Deploy Ingress

```bash
kubectl apply -f k8s/ingress.yaml
```

#### 9. Verify Deployment

```bash
# Check pod status
kubectl get pods -n trading-system

# Check services
kubectl get services -n trading-system

# Check ingress
kubectl get ingress -n trading-system

# Test API
curl https://your-domain.com/health
```

### Kubernetes Configuration Files

#### API Deployment

```yaml
# k8s/api-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: trading-api
  namespace: trading-system
spec:
  replicas: 3
  selector:
    matchLabels:
      app: trading-api
  template:
    metadata:
      labels:
        app: trading-api
    spec:
      containers:
      - name: api
        image: your-registry/trading-api:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: trading-config
        - secretRef:
            name: trading-secrets
        resources:
          limits:
            cpu: "1"
            memory: "1Gi"
          requests:
            cpu: "500m"
            memory: "512Mi"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

#### Ingress Configuration

```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: trading-ingress
  namespace: trading-system
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - trading.your-domain.com
    secretName: trading-tls
  rules:
  - host: trading.your-domain.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: trading-api
            port:
              number: 8000
      - path: /ws
        pathType: Prefix
        backend:
          service:
            name: trading-websocket
            port:
              number: 8081
      - path: /
        pathType: Prefix
        backend:
          service:
            name: trading-dashboard
            port:
              number: 8080
```

## ☁️ Cloud Installation

### AWS Deployment

#### Prerequisites
- **AWS CLI**: Configured with your credentials
- **AWS Account**: With appropriate permissions
- **Domain**: For SSL certificate

#### Step-by-Step AWS Deployment

1. **Create ECR Repository**
```bash
# Create ECR repositories
aws ecr create-repository --repository-name trading-api --region us-east-1
aws ecr create-repository --repository-name trading-dashboard --region us-east-1
aws ecr create-repository --repository-name trading-websocket --region us-east-1

# Get login token
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com
```

2. **Build and Push Images**
```bash
# Build images
docker build -t trading-api -f docker/Dockerfile.api .
docker build -t trading-dashboard -f docker/Dockerfile.dashboard .
docker build -t trading-websocket -f docker/Dockerfile.websocket .

# Tag for ECR
docker tag trading-api:latest <account>.dkr.ecr.us-east-1.amazonaws.com/trading-api:latest
docker tag trading-dashboard:latest <account>.dkr.ecr.us-east-1.amazonaws.com/trading-dashboard:latest
docker tag trading-websocket:latest <account>.dkr.ecr.us-east-1.amazonaws.com/trading-websocket:latest

# Push to ECR
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/trading-api:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/trading-dashboard:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/trading-websocket:latest
```

3. **Create RDS Database**
```bash
# Create PostgreSQL database
aws rds create-db-instance \
  --db-instance-identifier trading-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --master-username trading \
  --master-user-password <password> \
  --allocated-storage 20 \
  --db-name trading \
  --backup-retention-period 7
```

4. **Create ElastiCache (Redis)**
```bash
aws elasticache create-cache-cluster \
  --cache-cluster-id trading-redis \
  --cache-node-type cache.t3.micro \
  --engine redis \
  --num-cache-nodes 1
```

5. **Deploy with ECS/Fargate**
```bash
# Create ECS cluster
aws ecs create-cluster --cluster-name trading-cluster

# Create task definitions (see aws/task-definitions/ for examples)
aws ecs register-task-definition --cli-input-json file://aws/task-definitions/api-task.json
aws ecs register-task-definition --cli-input-json file://aws/task-definitions/dashboard-task.json
aws ecs register-task-definition --cli-input-json file://aws/task-definitions/websocket-task.json

# Create services
aws ecs create-service \
  --cluster trading-cluster \
  --service-name trading-api \
  --task-definition trading-api \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-12345,subnet-67890],securityGroups=[sg-abcdef],assignPublicIp=ENABLED}"
```

6. **Configure Load Balancer**
```bash
# Create Application Load Balancer
aws elbv2 create-load-balancer \
  --name trading-alb \
  --subnets subnet-12345 subnet-67890 \
  --security-groups sg-abcdef

# Create target groups
aws elbv2 create-target-group --name trading-api --protocol HTTP --port 8000 --vpc-id vpc-12345
aws elbv2 create-target-group --name trading-dashboard --protocol HTTP --port 8080 --vpc-id vpc-12345
aws elbv2 create-target-group --name trading-websocket --protocol HTTP --port 8081 --vpc-id vpc-12345

# Create listeners and rules
aws elbv2 create-listener \
  --load-balancer-arn <alb-arn> \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn=<api-target-group>
```

### Azure Deployment

#### Prerequisites
- **Azure CLI**: Configured with your subscription
- **Azure Subscription**: With appropriate permissions
- **Resource Group**: For organizing resources

#### Step-by-Step Azure Deployment

1. **Create Resource Group**
```bash
az group create --name trading-rg --location eastus
```

2. **Create Azure Container Registry**
```bash
az acr create --resource-group trading-rg --name tradingacr --sku Basic
az acr login --name tradingacr
```

3. **Build and Push Images**
```bash
# Build images
docker build -t trading-api -f docker/Dockerfile.api .
docker build -t trading-dashboard -f docker/Dockerfile.dashboard .
docker build -t trading-websocket -f docker/Dockerfile.websocket .

# Tag for ACR
docker tag trading-api tradingacr.azurecr.io/trading-api:latest
docker tag trading-dashboard tradingacr.azurecr.io/trading-dashboard:latest
docker tag trading-websocket tradingacr.azurecr.io/trading-websocket:latest

# Push to ACR
docker push tradingacr.azurecr.io/trading-api:latest
docker push tradingacr.azurecr.io/trading-dashboard:latest
docker push tradingacr.azurecr.io/trading-websocket:latest
```

4. **Create PostgreSQL Database**
```bash
az postgres server create \
  --resource-group trading-rg \
  --name trading-db \
  --location eastus \
  --admin-user trading \
  --admin-password <password> \
  --sku-name B_Gen5_1 \
  --version 15

az postgres db create \
  --resource-group trading-rg \
  --server-name trading-db \
  --name trading
```

5. **Create Redis Cache**
```bash
az redis create \
  --resource-group trading-rg \
  --name trading-redis \
  --location eastus \
  --sku Basic \
  --vm-size C0
```

6. **Deploy with Azure Container Instances**
```bash
# Create API container
az container create \
  --resource-group trading-rg \
  --name trading-api \
  --image tradingacr.azurecr.io/trading-api:latest \
  --cpu 1 \
  --memory 1 \
  --registry-login-server tradingacr.azurecr.io \
  --registry-username <acr-username> \
  --registry-password <acr-password> \
  --environment-variables TRADING_ENV=production DATABASE_URL=<db-url> \
  --ports 8000 \
  --dns-name-label trading-api

# Create dashboard container
az container create \
  --resource-group trading-rg \
  --name trading-dashboard \
  --image tradingacr.azurecr.io/trading-dashboard:latest \
  --cpu 1 \
  --memory 1 \
  --ports 8080 \
  --dns-name-label trading-dashboard
```

## 🔧 Post-Installation Configuration

### Database Setup

```bash
# Initialize database schema
docker-compose exec api python scripts/migrate.py

# Seed initial data (optional)
docker-compose exec api python scripts/seed.py
```

### SSL Certificate Setup

#### Let's Encrypt (Automated)
```bash
# Install certbot
sudo apt install certbot

# Get certificate
sudo certbot certonly --standalone -d your-domain.com

# Configure nginx to use certificates
sudo nano /etc/nginx/sites-available/trading
```

#### Manual Certificate
```bash
# Create certificate directory
sudo mkdir -p /etc/ssl/trading

# Copy certificates
sudo cp /path/to/cert.pem /etc/ssl/trading/
sudo cp /path/to/key.pem /etc/ssl/trading/

# Set permissions
sudo chmod 600 /etc/ssl/trading/key.pem
sudo chown root:root /etc/ssl/trading/*
```

### Backup Configuration

```bash
# Schedule database backups
crontab -e
# Add: 0 2 * * * docker-compose exec db pg_dump -U trading trading > /backups/trading_$(date +\%Y\%m\%d).sql

# Configure backup retention
# Add logrotate configuration for backup files
```

### Monitoring Setup

```bash
# Install Prometheus and Grafana
docker run -d -p 9090:9090 prom/prometheus
docker run -d -p 3000:3000 grafana/grafana

# Configure application metrics
# Add prometheus.yml configuration
# Import Grafana dashboards
```

### Log Aggregation

```bash
# Install ELK stack
docker run -d -p 5601:5601 -p 9200:9200 -p 5044:5044 sebp/elk

# Configure log shipping
# Update docker-compose.yml with logging configuration
```

## 🧪 Testing Installation

### Health Checks

```bash
# API health check
curl http://localhost:8000/health

# Detailed health
curl http://localhost:8000/api/v1/health/detailed

# Database connectivity
docker-compose exec api python -c "from src.infrastructure.database.duckdb_adapter import DuckDBAdapter; print('DB OK')"

# WebSocket connectivity
# Use browser developer tools or WebSocket client
```

### Functional Tests

```bash
# Run unit tests
python -m pytest tests/unit/ -v

# Run integration tests
python -m pytest tests/integration/ -v

# Run API tests
python -m pytest tests/api/ -v

# Load testing
python scripts/load_test.py
```

### Performance Tests

```bash
# Benchmark API endpoints
python scripts/benchmark.py

# Memory usage test
python scripts/memory_test.py

# Database performance test
python scripts/db_performance.py
```

## 🚨 Troubleshooting

### Common Installation Issues

#### Python Version Issues
```bash
# Check Python version
python --version

# Use specific Python version
python3.11 -m venv venv
source venv/bin/activate
```

#### Permission Issues
```bash
# Fix directory permissions
sudo chown -R $USER:$USER /path/to/trading-system

# Fix Docker permissions
sudo usermod -aG docker $USER
newgrp docker
```

#### Port Conflicts
```bash
# Find process using port
lsof -i :8000

# Change port in configuration
export API_PORT=8001
export DASHBOARD_PORT=8081
export WEBSOCKET_PORT=8082
```

#### Database Connection Issues
```bash
# Test database connection
docker-compose exec db psql -U trading -d trading -c "SELECT 1;"

# Check database logs
docker-compose logs db

# Reset database
docker-compose down -v
docker-compose up -d db
```

#### Memory Issues
```bash
# Check system memory
free -h

# Increase Docker memory limits
docker-compose.yml:
services:
  api:
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G
```

### Getting Help

- **Documentation**: Check troubleshooting section
- **Logs**: View application logs in `logs/` directory
- **Health Checks**: Use `/health` endpoints for diagnostics
- **Community**: Check GitHub issues and discussions

## 📈 Performance Optimization

### Database Optimization

```bash
# Analyze query performance
docker-compose exec db psql -U trading -d trading -c "EXPLAIN ANALYZE SELECT * FROM market_data;"

# Add database indexes
docker-compose exec api python scripts/add_indexes.py

# Optimize connection pool
# Update DATABASE_POOL_SIZE in .env
```

### Application Optimization

```bash
# Enable caching
export REDIS_URL=redis://localhost:6379
export CACHE_TTL=300

# Configure Gunicorn for production
# Update docker-compose.prod.yml with Gunicorn configuration

# Enable compression
# Configure nginx with gzip compression
```

### Monitoring Optimization

```bash
# Configure Prometheus scraping
# Update prometheus.yml with service endpoints

# Set up Grafana dashboards
# Import trading system dashboard templates

# Configure alerting rules
# Create alert rules for critical metrics
```

This comprehensive installation guide covers all deployment options from simple Docker development setup to complex enterprise Kubernetes deployments.
