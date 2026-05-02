# 🚀 Full Stack Server Deployment Guide

This guide covers the steps to deploy the entire Business Analytics stack (Frontend, Backend, and Databases) on a single Ubuntu VPS with a custom domain and SSL.

---

## 📋 Prerequisites

1.  **A VPS**: (DigitalOcean, AWS, Linode, etc.)
    -   **Minimum**: 4GB RAM, 2 CPUs.
    -   **OS**: Ubuntu 22.04 or 24.04 LTS.
2.  **A Domain Name**: (e.g., `analytics.yourcompany.com`)
3.  **DNS Access**: Ability to add "A" records for your domain.

---

## 🛠️ Step 1: Server Preparation

Connect to your server via SSH and install the required tools:

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Nginx (Reverse Proxy)
sudo apt install -y nginx certbot python3-certbot-nginx
```

---

## 📂 Step 2: Code Deployment

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/parthbansal6482/Business-Analytics-Agent.git
    cd Business-Analytics-Agent
    ```

2.  **Configure Environment Variables**:
    Create a root `.env` file and fill in your production values:
    ```bash
    cp .env.example .env
    nano .env
    ```
    **Critical Production Settings:**
    ```env
    # Use your real domains
    FRONTEND_URL=https://analytics.yourcompany.com
    VITE_API_URL=https://api.yourcompany.com
    
    # Ensure these point to Docker service names
    POSTGRES_URL=postgresql+asyncpg://user:password@postgres:5432/ecomm_agent
    QDRANT_URL=http://qdrant:6333
    REDIS_URL=redis://redis:6379
    ```

3.  **Start the Stack**:
    ```bash
    docker compose up -d --build
    ```

---

## 🛰️ Step 3: Nginx Reverse Proxy Configuration

We need to tell Nginx to route traffic from your domains to the Docker containers.

1.  **Create Configuration**:
    ```bash
    sudo nano /etc/nginx/sites-available/analytics
    ```
2.  **Paste the following (Update domain names!):**
    ```nginx
    # Frontend Redirect
    server {
        server_name analytics.yourcompany.com;
        location / {
            proxy_pass http://localhost:5173;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }

    # Backend API Redirect
    server {
        server_name api.yourcompany.com;
        location / {
            proxy_pass http://localhost:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }
    ```
3.  **Enable and Test**:
    ```bash
    sudo ln -s /etc/nginx/sites-available/analytics /etc/nginx/sites-enabled/
    sudo nginx -t
    sudo systemctl restart nginx
    ```

---

## 🔒 Step 4: SSL (HTTPS) with Certbot

Secure your domains with free Let's Encrypt certificates:

```bash
sudo certbot --nginx -d analytics.yourcompany.com -d api.yourcompany.com
```
*Follow the prompts to enable HTTPS redirects.*

---

## 🚀 Step 5: Final Check

Visit your domain `https://analytics.yourcompany.com`. Everything should be live and secure!

### 💡 Maintenance Tips
- **View Logs**: `docker compose logs -f`
- **Restart App**: `docker compose restart`
- **Update App**: `git pull && docker compose up -d --build`
