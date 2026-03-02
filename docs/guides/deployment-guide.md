# Alchymine — Production Deployment Guide

Complete step-by-step instructions for deploying Alchymine to DigitalOcean with
Cloudflare CDN/DDoS protection and Namecheap domain management.

**Architecture:**

```
User → Cloudflare (CDN + DDoS + SSL edge) → DigitalOcean Droplet → Docker Stack
         ↑                                          ↑
    DNS + caching                          Nginx → FastAPI / Next.js
    Free tier                              PostgreSQL / Redis / Celery
```

**Estimated cost:** $12-24/mo (DigitalOcean) + free (Cloudflare) + ~$10/yr (domain)

---

## Table of Contents

1. [Purchase Domain (Namecheap)](#step-1-purchase-domain-namecheap)
2. [Create DigitalOcean Account + Droplet](#step-2-create-digitalocean-account--droplet)
3. [Set Up Cloudflare (DNS + CDN + Security)](#step-3-set-up-cloudflare-dns--cdn--security)
4. [Point Domain to Cloudflare](#step-4-point-domain-to-cloudflare)
5. [Configure Cloudflare DNS Records](#step-5-configure-cloudflare-dns-records)
6. [SSH Into Your Droplet](#step-6-ssh-into-your-droplet)
7. [Run the Deployment Script](#step-7-run-the-deployment-script)
8. [Configure Cloudflare Security Settings](#step-8-configure-cloudflare-security-settings)
9. [Verify Everything Works](#step-9-verify-everything-works)
10. [Post-Launch Checklist](#step-10-post-launch-checklist)
11. [Ongoing Maintenance](#ongoing-maintenance)
12. [Troubleshooting](#troubleshooting)
13. [Scaling Guide](#scaling-guide)

---

## Step 1: Purchase Domain (Namecheap)

**Time: 5 minutes**

1. Go to [namecheap.com](https://www.namecheap.com/)
2. Search for your domain (e.g., `alchymine.com`)
3. Add to cart and purchase
   - Enable **WhoisGuard** (free privacy protection)
   - Skip any upsells (SSL, hosting, email) — we handle all of this ourselves
4. After purchase, go to **Dashboard → Domain List**
5. Note your domain name — you'll need it in every step below

> **Why Namecheap?** Cheapest registrar with free WHOIS privacy. We don't use their
> DNS, SSL, or hosting — just the domain registration.

---

## Step 2: Create DigitalOcean Account + Droplet

**Time: 10 minutes**

### Create Account

1. Go to [digitalocean.com](https://www.digitalocean.com/)
2. Sign up (GitHub sign-in works)
3. Add a payment method

### Create SSH Key (if you don't have one)

On your **local machine** (not the server), open a terminal:

```bash
# Generate SSH key pair
ssh-keygen -t ed25519 -C "your-email@example.com"

# When prompted for file location, press Enter for default (~/.ssh/id_ed25519)
# Set a passphrase (recommended) or press Enter for none

# Copy your public key to clipboard
cat ~/.ssh/id_ed25519.pub
```

Copy the output — you'll paste it into DigitalOcean.

### Create Droplet

1. Go to **Create → Droplets**
2. Configure:

| Setting            | Value                                                     |
| ------------------ | --------------------------------------------------------- |
| **Region**         | Choose closest to your users (e.g., NYC1, SFO3, LON1)     |
| **Image**          | Ubuntu 22.04 (LTS) x64                                    |
| **Size**           | **Basic → Regular** (shared CPU)                          |
| **Plan**           | **$24/mo** (4 GB RAM / 2 vCPUs / 80 GB SSD) — recommended |
|                    | Or $12/mo (2 GB / 1 vCPU / 50 GB) to start, upgrade later |
| **Authentication** | SSH keys → paste your public key from above               |
| **Hostname**       | `alchymine`                                               |

3. Click **Create Droplet**
4. **Copy the IP address** shown after creation (e.g., `164.92.xxx.xxx`)

> **Why this size?** Alchymine runs 7 Docker containers. The 4GB droplet gives
> comfortable headroom. You can start with 2GB and resize later via the
> DigitalOcean dashboard (takes ~1 minute, requires a brief reboot).

### Enable Backups (Recommended)

1. Go to your droplet → **Backups** tab
2. Enable weekly backups ($4.80/mo for the $24 droplet)
3. This gives you full server snapshots in case anything goes wrong

---

## Step 3: Set Up Cloudflare (DNS + CDN + Security)

**Time: 5 minutes**

### Create Account

1. Go to [cloudflare.com](https://www.cloudflare.com/)
2. Sign up for a free account
3. Click **Add a Site**
4. Enter your domain name (e.g., `alchymine.com`)
5. Select the **Free** plan → Continue

### Why Cloudflare?

Cloudflare sits between your users and your server. For free, you get:

- **CDN**: Static assets (CSS, JS, images) served from 300+ edge locations worldwide
- **DDoS protection**: Absorbs attack traffic before it reaches your server
- **SSL edge**: HTTPS termination at the edge (faster for users)
- **Bot protection**: Blocks scrapers and credential stuffers
- **Analytics**: See real traffic data without any tracking code
- **Caching**: Reduces server load by 60-80% for static content

---

## Step 4: Point Domain to Cloudflare

**Time: 5 minutes (+ up to 24h for propagation, usually under 1h)**

After adding your site to Cloudflare, it will show you two nameservers like:

```
aria.ns.cloudflare.com
duke.ns.cloudflare.com
```

### Update Namecheap Nameservers

1. Log in to [Namecheap](https://www.namecheap.com/) → **Domain List**
2. Click **Manage** next to your domain
3. Under **Nameservers**, change from "Namecheap BasicDNS" to **Custom DNS**
4. Enter the two Cloudflare nameservers:
   - `aria.ns.cloudflare.com`
   - `duke.ns.cloudflare.com`
5. Click the green checkmark to save

> **Note:** Your actual nameserver names will be different — use the ones
> Cloudflare gives you, not the examples above.

### Verify in Cloudflare

1. Back in Cloudflare, click **Check Nameservers**
2. Wait for confirmation email (usually 5-30 minutes, can take up to 24h)
3. Cloudflare dashboard will show your site as **Active**

---

## Step 5: Configure Cloudflare DNS Records

**Time: 3 minutes**

In Cloudflare, go to **DNS → Records** and add these records.

Replace `164.92.xxx.xxx` with your actual DigitalOcean droplet IP.

| Type | Name  | Content          | Proxy                  | TTL  |
| ---- | ----- | ---------------- | ---------------------- | ---- |
| A    | `@`   | `164.92.xxx.xxx` | Proxied (orange cloud) | Auto |
| A    | `www` | `164.92.xxx.xxx` | Proxied (orange cloud) | Auto |

### What "Proxied" means

- **Proxied (orange cloud ON)**: Traffic goes through Cloudflare → CDN, DDoS
  protection, caching, and your server's real IP is hidden
- **DNS only (grey cloud)**: Traffic goes direct to your server — no Cloudflare
  benefits

**Always keep the orange cloud ON for production.**

### Important: SSL Mode

1. Go to **SSL/TLS → Overview**
2. Set SSL mode to **Full (strict)**
   - This means: User ↔ Cloudflare (encrypted) ↔ Your Server (encrypted with valid cert)
   - Our deployment script installs a real Let's Encrypt certificate, so strict mode works

> **Do NOT use "Flexible" mode** — it sends traffic unencrypted between Cloudflare
> and your server, which defeats the purpose for personal data.

---

## Step 6: SSH Into Your Droplet

**Time: 2 minutes**

From your local terminal:

```bash
# SSH into your droplet (replace with your IP)
ssh root@164.92.xxx.xxx

# If you get a fingerprint prompt, type "yes"
```

### First-time connection checklist

Once you're in:

```bash
# Verify you're on the right machine
hostname
uname -a

# Check available resources
free -h
df -h
```

You should see Ubuntu 22.04 with the RAM/disk you selected.

---

## Step 7: Run the Deployment Script

**Time: 15-25 minutes (mostly Docker image builds)**

### Option A: One-line install (easiest)

```bash
# Clone and run
git clone https://github.com/realsammyt/Alchymine.git
cd Alchymine
bash infrastructure/scripts/deploy-digitalocean.sh
```

### Option B: If you already uploaded/cloned the repo

```bash
cd /path/to/Alchymine
bash infrastructure/scripts/deploy-digitalocean.sh
```

### What the script will ask you

```
Enter your domain name (e.g., alchymine.com): alchymine.com
Enter your email for SSL certificates and alerts: you@example.com
Enter your Anthropic API key (sk-ant-...): sk-ant-api03-your-key-here
```

### What the script does (10 steps)

| Step  | What                                               | Time       |
| ----- | -------------------------------------------------- | ---------- |
| 1/10  | Updates Ubuntu packages                            | ~1 min     |
| 2/10  | Installs Docker Engine + Compose                   | ~2 min     |
| 3/10  | Configures UFW firewall (SSH + HTTP + HTTPS only)  | ~10 sec    |
| 4/10  | Sets up fail2ban (SSH brute force protection)      | ~10 sec    |
| 5/10  | Creates non-root deploy user + clones repo         | ~30 sec    |
| 6/10  | Generates cryptographic secrets (.env.production)  | ~5 sec     |
| 7/10  | Obtains Let's Encrypt SSL certificate              | ~1 min     |
| 8/10  | Builds Docker images + starts all services         | ~10-20 min |
| 9/10  | Configures daily automated database backups (3 AM) | ~5 sec     |
| 10/10 | Enables unattended security updates                | ~10 sec    |

When complete, you'll see a full summary of everything that's running.

---

## Step 8: Configure Cloudflare Security Settings

**Time: 10 minutes**

Now that your server is running, configure Cloudflare for optimal security and
performance. All of these settings are in the free tier.

### SSL/TLS Settings

1. **SSL/TLS → Overview**: Set to **Full (strict)** (you should have done this in Step 5)
2. **SSL/TLS → Edge Certificates**:
   - Always Use HTTPS: **ON**
   - HTTP Strict Transport Security (HSTS): **Enable**
     - Max Age: 6 months
     - Include subdomains: ON
     - Preload: ON
   - Minimum TLS Version: **1.2**
   - Automatic HTTPS Rewrites: **ON**

### Firewall / Security Settings

1. **Security → Settings**:
   - Security Level: **Medium**
   - Challenge Passage: **30 minutes**
   - Browser Integrity Check: **ON**

2. **Security → WAF** (Web Application Firewall):
   - Managed Rules: **ON** (free tier includes basic rules)

3. **Security → Bots**:
   - Bot Fight Mode: **ON** (blocks known bad bots)

### Speed / Performance Settings

1. **Speed → Optimization → Content Optimization**:
   - Auto Minify: **ON** for JavaScript, CSS, HTML
   - Brotli: **ON** (better compression than gzip)
   - Early Hints: **ON**
   - Rocket Loader: **OFF** (can conflict with Next.js)

2. **Caching → Configuration**:
   - Caching Level: **Standard**
   - Browser Cache TTL: **Respect Existing Headers** (our Nginx already sets good cache headers)

3. **Caching → Cache Rules** (create a rule):
   - Name: "Cache static assets aggressively"
   - When: URI Path contains `/_next/static/`
   - Then: Cache eligible, Edge TTL = 1 month, Browser TTL = 1 year

### Page Rules (Optional but recommended)

Create these rules in **Rules → Page Rules**:

1. **Force HTTPS:**
   - URL: `http://*alchymine.com/*`
   - Setting: Always Use HTTPS

2. **Cache everything for static assets:**
   - URL: `*alchymine.com/_next/static/*`
   - Setting: Cache Level = Cache Everything, Edge Cache TTL = 1 month

---

## Step 9: Verify Everything Works

**Time: 5 minutes**

### From your local machine

```bash
# Check HTTPS is working
curl -I https://yourdomain.com

# Expected: HTTP/2 200, with cf-ray header (proves Cloudflare is active)
# Look for:
#   server: cloudflare
#   cf-ray: xxxxx-IAD
#   strict-transport-security: max-age=...

# Check API health
curl https://yourdomain.com/api/health

# Expected: {"status": "ok"} or similar JSON response

# Check that HTTP redirects to HTTPS
curl -I http://yourdomain.com
# Expected: 301/302 redirect to https://
```

### From your browser

1. Visit `https://yourdomain.com` — you should see the Alchymine app
2. Open DevTools (F12) → Network tab → reload the page
   - Look for `cf-cache-status: HIT` on static assets (means Cloudflare CDN is working)
   - Look for the green lock icon (valid SSL)

### On the server

```bash
# SSH into server
ssh root@164.92.xxx.xxx

# Switch to deploy user
su - alchymine
cd ~/Alchymine/infrastructure

# Check all services are healthy
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps

# Expected output — all services should show "healthy":
#   alchymine-api      running (healthy)
#   alchymine-web      running (healthy)
#   alchymine-worker   running (healthy)
#   alchymine-db       running (healthy)
#   alchymine-redis    running (healthy)
#   alchymine-nginx    running (healthy)
#   alchymine-certbot  running

# View live logs
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f --tail=50
```

---

## Step 10: Post-Launch Checklist

Run through this checklist after your first successful deployment.

### Security

- [ ] SSH key-only access (password auth disabled)
- [ ] UFW firewall active (only 22, 80, 443)
- [ ] fail2ban running (`sudo fail2ban-client status sshd`)
- [ ] `.env.production` has chmod 600
- [ ] All secrets are unique (not default values)
- [ ] Cloudflare SSL set to Full (strict)
- [ ] HSTS enabled in Cloudflare
- [ ] DigitalOcean droplet backups enabled

### Performance

- [ ] Cloudflare CDN active (orange cloud on DNS records)
- [ ] Static assets showing `cf-cache-status: HIT` in browser DevTools
- [ ] Brotli compression enabled in Cloudflare
- [ ] Nginx gzip compression active (fallback for non-Cloudflare requests)

### Monitoring

- [ ] Set up DigitalOcean Monitoring (free):
  - Droplet → Graphs → Enable advanced monitoring
  - Set alerts for CPU > 80%, Disk > 90%, Memory > 90%
- [ ] Set up Cloudflare notifications:
  - Notifications → Create → DDoS attack alerts
  - Notifications → Create → SSL certificate expiration

### Backups

- [ ] Automated database backup cron running (`crontab -l` as alchymine user)
- [ ] DigitalOcean weekly snapshots enabled
- [ ] Test a backup/restore cycle:

  ```bash
  # Create manual backup
  bash infrastructure/scripts/backup-db.sh ./backups

  # Verify backup file exists and has content
  ls -la ./backups/
  ```

---

## Ongoing Maintenance

### Automated Release Pipeline

Alchymine uses a GitHub-based release pipeline for deployments. No manual SSH
is required for routine deploys.

#### How it works

```
Merge PR to main
  → CI runs (lint, test, build) ✅
  → prepare-release.yml auto-creates a DRAFT GitHub Release
      - Version bump detected from commit messages (feat → minor, fix → patch)
      - Changelog generated from conventional commits
  → You review the draft release on GitHub
  → You click "Publish release"
  → release.yml fires:
      - Builds Docker images (api, web)
      - Pushes to GHCR with semver tags
      - SSHs into DigitalOcean droplet
      - Pulls new images, restarts containers
      - Verifies health endpoints
  → Production updated ✅
```

#### Required GitHub Secrets

Go to **GitHub → Settings → Secrets and variables → Actions → New repository secret**
and add these three secrets:

| Secret | Value | How to get it |
|--------|-------|---------------|
| `DEPLOY_HOST` | Droplet IP address (e.g., `164.92.xxx.xxx`) | DigitalOcean dashboard → Droplets |
| `DEPLOY_USER` | `alchymine` | The deploy user created by `deploy-digitalocean.sh` |
| `DEPLOY_SSH_KEY` | Private SSH key (full PEM content) | Generate with `ssh-keygen -t ed25519`, add public key to droplet's `~alchymine/.ssh/authorized_keys` |

#### GitHub Environment (optional)

If you want an extra approval gate before deployment (beyond just publishing the
release), create a GitHub Environment:

1. Go to **GitHub → Settings → Environments → New environment**
2. Name it `production`
3. Enable **Required reviewers** (adds a manual approval step in the workflow)

The deploy job references `environment: production` — if the environment doesn't
exist, GitHub creates it automatically with no protection rules.

### Manual Deployment

For emergency fixes or when the pipeline isn't available:

```bash
# SSH in and switch to deploy user
ssh root@your-server-ip
su - alchymine
cd ~/Alchymine

# Fetch and checkout the release tag
git fetch --tags
git checkout v<version>

# Pull images and restart
cd infrastructure
docker compose -f docker-compose.yml -f docker-compose.prod.yml pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --remove-orphans

# Watch logs to make sure everything starts clean
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f --tail=20
```

### Viewing Logs

```bash
cd ~/Alchymine/infrastructure

# All services
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f

# Specific service
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f api
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f web
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f worker
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f nginx
```

### Database Backups

```bash
# Manual backup
bash ~/Alchymine/infrastructure/scripts/backup-db.sh ~/Alchymine/backups

# Restore from backup (careful — drops existing database!)
bash ~/Alchymine/infrastructure/scripts/restore-db.sh ~/Alchymine/backups/alchymine_YYYYMMDD_HHMMSS.sql.gz

# Check backup cron is running
crontab -l
```

### SSL Certificate Renewal

Handled automatically by the Certbot container (checks every 12 hours). To
manually check or force renewal:

```bash
# Check cert expiry
docker exec alchymine-certbot certbot certificates

# Force renewal (if needed)
docker exec alchymine-certbot certbot renew --force-renewal
docker compose -f docker-compose.yml -f docker-compose.prod.yml restart nginx
```

### Upgrading the Droplet

If you need more resources:

1. Go to DigitalOcean → Droplet → **Resize**
2. Choose the new plan (e.g., $24 → $48 for 8GB RAM)
3. Select "Resize droplet" (keeps disk, just adds RAM/CPU)
4. Wait ~1 minute for reboot
5. SSH back in — everything restarts automatically (Docker services have `restart: always`)

---

## Troubleshooting

### "502 Bad Gateway" from Cloudflare

**Cause:** Your origin server (DigitalOcean) isn't responding.

```bash
# SSH in and check if services are running
ssh root@your-server-ip
su - alchymine
cd ~/Alchymine/infrastructure
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps

# If services are down, restart them
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Check logs for errors
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs --tail=50 api
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs --tail=50 nginx
```

### "SSL Handshake Failed" / Error 525

**Cause:** Cloudflare can't establish SSL with your server.

```bash
# Check if SSL cert exists
docker exec alchymine-nginx ls -la /etc/letsencrypt/live/

# If missing, re-run SSL setup
cd ~/Alchymine/infrastructure/scripts
bash init-ssl.sh

# Then restart nginx
cd ~/Alchymine/infrastructure
docker compose -f docker-compose.yml -f docker-compose.prod.yml restart nginx
```

Also verify Cloudflare SSL mode is "Full (strict)" not "Flexible".

### Docker containers keep restarting

```bash
# Check which container is failing
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps

# View its logs
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs --tail=100 <service-name>

# Common causes:
# - api: Missing .env.production values, database not ready
# - web: Build failed, missing env vars
# - db: Wrong password, disk full
# - redis: Memory limit reached
```

### Can't SSH in

```bash
# If locked out, use DigitalOcean's web console:
# Droplet → Access → Launch Recovery Console

# Check if fail2ban blocked you
sudo fail2ban-client status sshd

# Unban your IP
sudo fail2ban-client set sshd unbanip YOUR_IP_ADDRESS
```

### Database is full / disk space issues

```bash
# Check disk usage
df -h

# Check Docker disk usage
docker system df

# Clean up unused Docker images/volumes
docker system prune -a --volumes
# WARNING: This removes ALL stopped containers, unused images, and unnamed volumes.
# Only run this if you're sure you don't need them.

# Check backup directory size
du -sh ~/Alchymine/backups/
```

### Cloudflare showing stale content

```bash
# Purge Cloudflare cache
# Go to Cloudflare → Caching → Configuration → Purge Everything

# Or purge specific URLs via API (if you have your zone ID):
# curl -X POST "https://api.cloudflare.com/client/v4/zones/YOUR_ZONE_ID/purge_cache" \
#   -H "Authorization: Bearer YOUR_API_TOKEN" \
#   -H "Content-Type: application/json" \
#   --data '{"purge_everything":true}'
```

---

## Scaling Guide

### When to upgrade

| Symptom                         | Fix                                           |
| ------------------------------- | --------------------------------------------- |
| API responses > 500ms           | Upgrade droplet (more CPU) or add API workers |
| Memory usage > 85% consistently | Upgrade to next droplet size                  |
| Disk > 80%                      | Resize disk or clean old backups/images       |
| 1000+ concurrent users          | Move to managed Kubernetes (DOKS)             |

### Horizontal scaling path

```
Phase 1: Single droplet ($12-24/mo)
  └── Everything on one machine, Docker Compose
  └── Good for 0-1000 users

Phase 2: Managed services ($50-100/mo)
  └── Move PostgreSQL → DigitalOcean Managed Database ($15/mo)
  └── Move Redis → DigitalOcean Managed Redis ($15/mo)
  └── Keep app services on droplet
  └── Good for 1000-5000 users

Phase 3: Container orchestration ($100-300/mo)
  └── Move to DigitalOcean Kubernetes (DOKS)
  └── Separate API, worker, web into individual deployable services
  └── Auto-scaling based on load
  └── Good for 5000-50000+ users
```

### DigitalOcean Managed Database (Phase 2)

When you're ready to separate the database:

1. Go to DigitalOcean → **Databases → Create**
2. Choose PostgreSQL 15, same region as droplet
3. $15/mo for 1 GB RAM / 1 vCPU / 10 GB storage
4. Update `.env.production` DATABASE_URL to the managed DB connection string
5. Remove the `db` service from docker-compose
6. Restart the stack

This gives you automatic backups, failover, and connection pooling without
managing PostgreSQL yourself.

---

## Quick Reference Card

```
┌──────────────────────────────────────────────────────────────┐
│                    ALCHYMINE DEPLOYMENT                      │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Domain registrar:  namecheap.com                            │
│  DNS + CDN:         cloudflare.com (Free tier)               │
│  Server:            digitalocean.com ($12-24/mo)             │
│                                                              │
│  SSH:        ssh root@YOUR_IP                                │
│  Deploy user: su - alchymine                                 │
│  App dir:    ~/Alchymine                                     │
│  Infra dir:  ~/Alchymine/infrastructure                      │
│                                                              │
│  Start:      docker compose -f docker-compose.yml            │
│              -f docker-compose.prod.yml up -d                │
│                                                              │
│  Stop:       docker compose -f docker-compose.yml            │
│              -f docker-compose.prod.yml down                 │
│                                                              │
│  Logs:       docker compose -f docker-compose.yml            │
│              -f docker-compose.prod.yml logs -f              │
│                                                              │
│  Status:     docker compose -f docker-compose.yml            │
│              -f docker-compose.prod.yml ps                   │
│                                                              │
│  Backup:     bash infrastructure/scripts/backup-db.sh        │
│              ./backups                                        │
│                                                              │
│  SSL:        Automatic (Certbot checks every 12h)            │
│  Updates:    Automatic (unattended-upgrades)                  │
│  Backups:    Automatic (daily at 3 AM)                        │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```
