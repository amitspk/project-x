# Nginx + SSL Setup for VPS

## 1) DNS
Create A records pointing to your VPS IP:
- `api.yourdomain.com` → VPS_IP
- `me.yourdomain.com` → VPS_IP (Mongo Express)
- `pg.yourdomain.com` → VPS_IP (pgAdmin)

## 2) Install Nginx & Certbot
```bash
sudo apt update && sudo apt install -y nginx certbot python3-certbot-nginx
sudo systemctl enable nginx && sudo systemctl start nginx
```

## 3) Copy site configs
On VPS, create files in `/etc/nginx/sites-available/` with the contents of:
- `fyi-widget-api.conf`
- `fyi-widget-mongo-express.conf`
- `fyi-widget-pgadmin.conf`

```bash
sudo tee /etc/nginx/sites-available/fyi-widget-api <<'EOF'
$(sed 's/.*/&/' nginx/sites/fyi-widget-api.conf)
EOF

sudo tee /etc/nginx/sites-available/fyi-widget-mongo-express <<'EOF'
$(sed 's/.*/&/' nginx/sites/fyi-widget-mongo-express.conf)
EOF

sudo tee /etc/nginx/sites-available/fyi-widget-pgadmin <<'EOF'
$(sed 's/.*/&/' nginx/sites/fyi-widget-pgadmin.conf)
EOF
```

Enable sites:
```bash
sudo ln -s /etc/nginx/sites-available/fyi-widget-api /etc/nginx/sites-enabled/
sudo ln -s /etc/nginx/sites-available/fyi-widget-mongo-express /etc/nginx/sites-enabled/
sudo ln -s /etc/nginx/sites-available/fyi-widget-pgadmin /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

## 4) Obtain SSL certificates (Let’s Encrypt)
```bash
sudo certbot --nginx -d api.yourdomain.com
sudo certbot --nginx -d me.yourdomain.com
sudo certbot --nginx -d pg.yourdomain.com
```

Auto-renew test:
```bash
sudo certbot renew --dry-run
```

## 5) (Optional) Add extra Basic Auth for admin UIs
```bash
sudo apt install -y apache2-utils
sudo htpasswd -c /etc/nginx/.htpasswd-mongo admin
sudo htpasswd -c /etc/nginx/.htpasswd-pgadmin admin

# Uncomment auth_basic lines in the mongo-express/pgadmin server blocks, then:
sudo nginx -t && sudo systemctl reload nginx
```

## 6) Security checklist
- Keep database ports internal only (compose binds to 127.0.0.1)
- Use strong passwords in `.env` (chmod 600)
- Limit admin UIs to Basic Auth + strong passwords
- Consider IP allowlists if possible


