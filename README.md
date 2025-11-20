# Documentation for Telegram Bot with FastAPI and ngrok

## Project Description

This project is a Telegram bot written in Python using FastAPI. The bot sends daily currency exchange rates every morning and has a function to get the current rate on demand. For Telegram API to access the local server, ngrok is used to provide an HTTPS tunnel.

---

## Architecture and Interaction with Telegram API

### Telegram API Connection Requirements

Telegram API requires all requests (including webhooks) to be made over HTTPS (SSL/TLS). Requests without a secure connection are not accepted to ensure the security of data transmission. This is an important consideration when deploying a webhook for the bot.

### Using ngrok

To bypass the lack of direct SSL on the local server, ngrok is used. Ngrok creates a public HTTPS tunnel to the local server port.

- ngrok configuration (`/home/admin/.config/ngrok/ngrok.yml`):
```
version: 3

agent:
authtoken: <YOUR_AUTH_TOKEN>
api_key: <YOUR_API_KEY>

tunnels:
bot:
proto: http
addr: 8008
```

- Start via systemd service (`/etc/systemd/system/ngrok.service`):

```
[Unit]
Description=Ngrok tunnel for tg-bot-cur-rate
After=network.target
Requires=docker.service

[Service]
User=admin
WorkingDirectory=/home/admin
ExecStart=/usr/bin/bash -c "ngrok start --config /home/admin/.config/ngrok/ngrok.yml bot"
ExecStartPost=/usr/bin/bash -c "/usr/local/bin/update_webhook.sh"
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
EnvironmentFile=/home/admin/git-repos/tg-bot-fastapi-nginx/.env

[Install]
WantedBy=multi-user.target
```


- Webhook update script (`/usr/local/bin/update_webhook.sh`):
```
#!/bin/bash
sleep 5
BASE_URL=$(curl -s 'http://127.0.0.1:4040/api/tunnels' | jq -r '.tunnels.public_url')

if [ -n "$BASE_URL" ]; then
echo "Registering webhook for Telegram bot..."
curl -s "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook"
-d "url=${BASE_URL}/webhook/${TG_SECRET}"
-d "secret_token=${TG_SECRET}"
echo "New url $BASE_URL"
else
echo "❌ Ngrok URL not found. Skipping webhook registration."
fi
```


# Explanation:

- ngrok creates a public HTTPS URL used to register the webhook with Telegram.
- The local server accepts HTTP requests on port 8008, and ngrok proxies them over HTTPS.
- This approach meets Telegram API security and encryption requirements.

---

## Task Scheduler (cron)

For automatically sending the currency rate in the morning, a cron job is used:

```
0 2 * * * curl -s "http://127.0.0.1:8008/cron" >/dev/null 2>&1
```


This job triggers the internal endpoint every morning at 2:00 AM to send the currency rate.

---

## Summary

- Telegram API does not accept webhook requests without SSL/TLS.
- ngrok is used as an HTTPS proxy to the local server to provide secure connections.
- The webhook is registered using the dynamic public HTTPS URL nginx provides.
- The cron scheduler automates daily currency rate notifications.

---

## Recommendations for Future Work

- Keep secrets and tokens in `.env` files and avoid public disclosure.
- Consider using a permanent HTTPS proxy or certificates for your own server to avoid dependency on ngrok.
- Document and automate service deployment with Docker and systemd.


