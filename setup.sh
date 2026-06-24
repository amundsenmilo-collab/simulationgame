#!/bin/bash
# Digital Ocean Droplet Setup for Asford Materials Engine

set -e

echo "=== Asford Materials Hyperrealism Engine Setup ==="

# Update system
apt update && apt upgrade -y

# Install dependencies
apt install -y python3-pip python3-venv git nginx sqlite3

# Create app directory
mkdir -p /opt/asford
cd /opt/asford

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python packages
pip install --upgrade pip
pip install fastapi uvicorn pydantic transformers torch sqlite3 requests

# For CPU-only (4GB RAM droplet):
pip install torch --index-url https://download.pytorch.org/whl/cpu

# For GPU (if you upgrade to GPU droplet later):
# pip install torch

# Download Hugging Face model (Llama 3.1 8B)
# This requires huggingface-cli login or token
echo "Downloading Llama 3.1 8B..."
python3 -c "
from transformers import AutoModelForCausalLM, AutoTokenizer
model = AutoModelForCausalLM.from_pretrained('meta-llama/Llama-3.1-8B-Instruct')
tokenizer = AutoTokenizer.from_pretrained('meta-llama/Llama-3.1-8B-Instruct')
"

# Initialize database
sqlite3 asford.db < schema.sql

# Create systemd service
cat > /etc/systemd/system/asford.service << 'EOF'
[Unit]
Description=Asford Materials Hyperrealism Engine
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/asford
Environment=PATH=/opt/asford/venv/bin
Environment=PYTHONPATH=/opt/asford
Environment=SERPAPI_KEY=your_key_here
ExecStart=/opt/asford/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable asford

# Nginx reverse proxy
cat > /etc/nginx/sites-available/asford << 'EOF'
server {
    listen 80;
    server_name your-droplet-ip;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF

ln -sf /etc/nginx/sites-available/asford /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx

echo "=== Setup Complete ==="
echo "Start the server: systemctl start asford"
echo "Check status: systemctl status asford"
echo "API docs: http://your-droplet-ip/docs"
