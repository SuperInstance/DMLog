# DMLog Installation Guide

Complete installation instructions for the DMLog temporal consciousness D&D system.

## Table of Contents

- [System Requirements](#system-requirements)
- [Installation Methods](#installation-methods)
- [Configuration](#configuration)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)
- [Advanced Setup](#advanced-setup)

---

## System Requirements

### Minimum Requirements

- **CPU**: 2 cores
- **RAM**: 4 GB
- **Storage**: 10 GB free space
- **Python**: 3.10 or higher
- **Docker**: 20.10+ (for Docker installation)

### Recommended Requirements

- **CPU**: 4+ cores
- **RAM**: 8+ GB
- **Storage**: 20+ GB SSD
- **Python**: 3.11
- **Docker**: Latest stable version

### External Services

- **OpenAI API Key**: Required for LLM features (GPT-4 access)
- **Qdrant**: Vector database (runs in Docker)
- **Optional**: Anthropic API key for Claude access

---

## Installation Methods

### Option 1: Docker (Recommended)

Docker installation is the simplest and ensures all dependencies are properly configured.

#### Step 1: Install Docker

**Ubuntu/Debian:**
```bash
# Update package index
sudo apt-get update

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt-get install docker-compose-plugin

# Verify installation
docker --version
docker compose version
```

**macOS:**
```bash
# Download and install Docker Desktop from
# https://www.docker.com/products/docker-desktop
```

**Windows:**
```bash
# Download and install Docker Desktop from
# https://www.docker.com/products/docker-desktop
# Ensure WSL 2 is enabled
```

#### Step 2: Clone the Repository

```bash
# Navigate to your desired location
cd /path/to/projects

# If you have the source files
cd /mnt/c/users/casey/project\ archive/DMLog-Complete-Package/DMLog-Complete-Package/source_code
```

#### Step 3: Configure Environment

```bash
# Copy the environment template
cp .env.example .env

# Edit .env with your preferred editor
nano .env  # or vim, code, etc.
```

**Required settings in `.env`:**
```bash
# API Keys (REQUIRED)
OPENAI_API_KEY=sk-your-openai-api-key-here

# Optional API Keys
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here

# Model Settings
DEFAULT_MODEL=gpt-4

# Service URLs
QDRANT_URL=http://qdrant:6333
```

#### Step 4: Start Services

```bash
# Build and start all services
docker compose up -d

# View logs
docker compose logs -f

# Check service status
docker compose ps
```

Services started:
- **API Server**: `http://localhost:8000`
- **Qdrant Vector DB**: `http://localhost:6333`
- **Dashboard**: `http://localhost:8000/docs` (FastAPI auto-docs)

#### Step 5: Verify Installation

```bash
# Health check
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","services":{"qdrant":"connected","database":"connected"}}
```

---

### Option 2: Local Python Installation

For development or when Docker is not available.

#### Step 1: Install Python Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install python3.11 python3.11-venv python3-pip
```

**macOS:**
```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python
brew install python@3.11
```

**Windows:**
```bash
# Download Python 3.11+ from https://www.python.org/downloads/
# During installation, check "Add Python to PATH"
```

#### Step 2: Create Virtual Environment

```bash
cd backend

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate
```

#### Step 3: Install Python Packages

```bash
# Upgrade pip
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt
```

#### Step 4: Start Qdrant (Required)

**Using Docker:**
```bash
docker run -d \
  --name qdrant \
  -p 6333:6333 \
  -v $(pwd)/data/qdrant_storage:/qdrant/storage \
  qdrant/qdrant:latest
```

**Using Qdrant binary:**
```bash
# Download Qdrant
curl -L https://github.com/qdrant/qdrant/releases/latest/download/qdrant-linux-x86_64.tar.gz | tar xz

# Run Qdrant
./qdrant
```

#### Step 5: Configure Environment

```bash
# Create .env file
cat > .env << EOF
OPENAI_API_KEY=sk-your-key-here
QDRANT_URL=http://localhost:6333
DEFAULT_MODEL=gpt-4
EOF
```

#### Step 6: Run the API Server

```bash
# From the backend directory
python api_server.py

# Or using uvicorn directly
uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
```

#### Step 7: Verify Installation

```bash
# From another terminal
curl http://localhost:8000/health
```

---

## Configuration

### Environment Variables

Create a `.env` file with the following variables:

#### Required Variables

```bash
# OpenAI API Key (REQUIRED for LLM features)
OPENAI_API_KEY=sk-your-openai-api-key-here
```

#### Optional Variables

```bash
# API Configuration
API_HOST=0.0.0.0          # Host to bind to
API_PORT=8000             # Port to bind to
DEBUG=false               # Enable debug mode

# LLM Configuration
ANTHROPIC_API_KEY=sk-ant-...  # Anthropic API key (optional)
DEFAULT_MODEL=gpt-4            # Default model to use
TEMPERATURE=0.7                 # Default temperature
MAX_TOKENS=2000                 # Default max tokens

# Qdrant Configuration
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=              # Leave empty for local

# Storage Paths
DATA_PATH=./data
VECTOR_STORAGE_PATH=./data/qdrant_storage
LOGS_PATH=./logs

# Decision Thresholds (can be customized per character)
BOT_MIN_CONFIDENCE=0.7
BRAIN_MIN_CONFIDENCE=0.5
HIGH_STAKES_THRESHOLD=0.7
CRITICAL_STAKES_THRESHOLD=0.9
```

### Custom Thresholds

You can customize decision escalation thresholds per character:

```python
from escalation_engine import EscalationEngine, EscalationThresholds

engine = EscalationEngine()

# Set custom thresholds for a character
custom_thresholds = EscalationThresholds(
    bot_min_confidence=0.8,        # More strict
    brain_min_confidence=0.6,
    high_stakes_threshold=0.8,     # More conservative
    hp_critical_threshold=0.3
)

engine.set_thresholds("character_id", custom_thresholds)
```

---

## Verification

### Health Check

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "services": {
    "qdrant": "connected",
    "database": "connected"
  },
  "version": "1.0.0"
}
```

### Run Test Suite

```bash
cd backend

# Run all tests
python test_escalation_engine.py
python test_memory_system.py
python test_vector_memory.py

# Or use pytest if installed
pytest test_*.py -v
```

### Create Test Character

```bash
curl -X POST http://localhost:8000/characters/create \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Character",
    "race": "Human",
    "class_name": "Fighter",
    "level": 1,
    "strength": 16,
    "dexterity": 12,
    "constitution": 14,
    "intelligence": 10,
    "wisdom": 11,
    "charisma": 8
  }'
```

---

## Troubleshooting

### Issue: Docker won't start

**Symptoms:** `docker compose up` fails

**Solutions:**
```bash
# Check Docker is running
docker ps

# Restart Docker daemon
sudo systemctl restart docker  # Linux
# Or restart Docker Desktop (Windows/macOS)

# Check port conflicts
netstat -tuln | grep 8000
netstat -tuln | grep 6333

# Change ports in docker-compose.yml if needed
```

### Issue: Qdrant connection refused

**Symptoms:** API logs show Qdrant connection errors

**Solutions:**
```bash
# Check Qdrant is running
docker ps | grep qdrant

# Check Qdrant logs
docker compose logs qdrant

# Restart Qdrant
docker compose restart qdrant

# Verify Qdrant is accessible
curl http://localhost:6333/collections
```

### Issue: OpenAI API errors

**Symptoms:** 401 Unauthorized or quota exceeded

**Solutions:**
```bash
# Verify API key is set
echo $OPENAI_API_KEY

# Test API key directly
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# Check quota and billing at
# https://platform.openai.com/account/usage
```

### Issue: Python module import errors

**Symptoms:** `ModuleNotFoundError: No module named 'xyz'`

**Solutions:**
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # Linux/macOS

# Reinstall requirements
pip install -r requirements.txt --upgrade

# Check Python version
python --version  # Should be 3.10+
```

### Issue: Port already in use

**Symptoms:** `Address already in use` error

**Solutions:**
```bash
# Find process using port
lsof -i :8000  # Linux/macOS
netstat -ano | findstr :8000  # Windows

# Kill the process or use different port
# Edit .env: API_PORT=8001
```

### Issue: Memory/Performance problems

**Symptoms:** Slow responses, high memory usage

**Solutions:**
```bash
# Check available memory
free -h  # Linux
vm_stat  # macOS

# Reduce memory usage by:
# 1. Using smaller models (gpt-3.5-turbo instead of gpt-4)
# 2. Reducing retrieval top_k in memory queries
# 3. Enabling data cleanup in training_data_collector

# Configure in .env:
DEFAULT_MODEL=gpt-3.5-turbo
MEMORY_TOP_K=5  # Instead of 10
```

---

## Advanced Setup

### Production Deployment

#### Using Systemd (Linux)

Create `/etc/systemd/system/dmlog.service`:

```ini
[Unit]
Description=DMLog API Server
After=network.target

[Service]
Type=simple
User=dmlog
WorkingDirectory=/opt/dmlog/backend
Environment="PATH=/opt/dmlog/venv/bin"
ExecStart=/opt/dmlog/venv/bin/uvicorn api_server:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable dmlog
sudo systemctl start dmlog
sudo systemctl status dmlog
```

#### Using Nginx Reverse Proxy

Create `/etc/nginx/sites-available/dmlog`:

```nginx
upstream dmlog {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name dmlog.example.com;

    location / {
        proxy_pass http://dmlog;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable:
```bash
sudo ln -s /etc/nginx/sites-available/dmlog /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Multi-Instance Setup

For running multiple game instances:

```bash
# Create separate environment files
cp .env .env.instance1
cp .env .env.instance2

# Edit each with different ports
# .env.instance1: API_PORT=8001
# .env.instance2: API_PORT=8002

# Start each instance
docker compose --env-file .env.instance1 up -d
docker compose --env-file .env.instance2 up -d
```

### Custom Model Routing

Configure model selection based on decision complexity:

```python
from model_routing import ModelRouter, ModelTier

router = ModelRouter()

# Configure tiers
router.configure_tier(
    ModelTier.FAST,
    model="gpt-3.5-turbo",
    max_tokens=500
)

router.configure_tier(
    ModelTier.STANDARD,
    model="gpt-4",
    max_tokens=2000
)

router.configure_tier(
    ModelTier.COMPLEX,
    model="gpt-4-32k",
    max_tokens=4000
)
```

### Backup and Restore

#### Backup Database

```bash
# SQLite backup
cp backend/data/decisions.db backups/decisions_$(date +%Y%m%d).db

# Qdrant backup (using snapshot API)
curl -X POST http://localhost:6333/collections/{collection_name}/snapshots
```

#### Restore Database

```bash
# SQLite restore
cp backups/decisions_20240101.db backend/data/decisions.db

# Qdrant restore
# Upload snapshot and recover via Qdrant API
```

---

## Development Setup

### For Contributors

```bash
# Clone repository
git clone https://github.com/your-org/dmlog.git
cd dmlog

# Create development environment
python3 -m venv venv
source venv/bin/activate

# Install development dependencies
pip install -r requirements.txt
pip install pytest pytest-cov black mypy

# Run tests with coverage
pytest --cov=. --cov-report=html

# Format code
black backend/

# Type checking
mypy backend/
```

### Running Tests

```bash
cd backend

# All tests
pytest test_*.py -v

# Specific module
pytest test_escalation_engine.py -v

# With coverage
pytest test_escalation_engine.py --cov=escalation_engine --cov-report=term-missing

# Performance profiling
pytest test_escalation_engine.py -v --profile
```

---

## Next Steps

After installation:

1. **Read the [API Documentation](API.md)** for complete module reference
2. **Review [Architecture](ARCHITECTURE.md)** for system understanding
3. **Check [README](../README.md)** for usage examples
4. **Run the test suite** to verify everything works
5. **Create your first campaign** using the Quick Start guide

---

## Support

For additional help:

- Check existing issues on GitHub
- Review the test files for usage examples
- Consult the API documentation for specific modules
- See the troubleshooting section above
