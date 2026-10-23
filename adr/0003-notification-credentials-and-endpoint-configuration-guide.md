# ADR 0003: Comprehensive Guide to Notification Credentials, Endpoints, and Configuration

## Status
Accepted

## Context
`alert-engine` dispatches critical alerts across 15 notification and incident management platforms. To adhere to strict security, compliance, and cloud-native practices:
1. No external URLs, API tokens, webhook addresses, or routing keys may be hardcoded in Python code.
2. All parameters must be supplied via runtime environment variables or injected from secret managers into container deployment manifests (Docker Compose, Kubernetes, Helm).
3. Operators and platform engineers require clear, definitive documentation explaining where and how to obtain credentials, tokens, and endpoints for each integrated platform.

---

## Service Credential Acquisition Guide

### 1. Slack (`SlackAdapter`)
- **Required Variable**: `SLACK_WEBHOOK_URL`
- **Optional Variable**: `SLACK_TIMEOUT_SECONDS`
- **How to Obtain**:
  1. Go to [api.slack.com/apps](https://api.slack.com/apps) and create or select an application.
  2. Under **Features**, select **Incoming Webhooks** and toggle it **On**.
  3. Click **Add New Webhook to Workspace**, select the default fallback channel, and authorize.
  4. Copy the Webhook URL (format: `https://hooks.slack.com/services/T.../B.../...`).

### 2. PagerDuty (`PagerDutyAdapter`)
- **Required Variables**: `PAGERDUTY_ROUTING_KEY`, `PAGERDUTY_ENDPOINT`
- **Standard Public Endpoint**: `https://events.pagerduty.com/v2/enqueue`
- **How to Obtain**:
  1. In the PagerDuty console, navigate to **Services** -> **Service Directory**.
  2. Click into the destination service -> go to the **Integrations** tab.
  3. Click **Add integration** -> select **Events API v2** -> save.
  4. Copy the 32-character hexadecimal **Integration Key** (`PAGERDUTY_ROUTING_KEY`).

### 3. Microsoft Teams (`TeamsAdapter`)
- **Required Variable**: `TEAMS_WEBHOOK_URL`
- **How to Obtain**:
  1. In Microsoft Teams, navigate to the target channel.
  2. Click **...** (More options) -> **Connectors** (or **Workflows**).
  3. Search for **Incoming Webhook** (or "Post to a channel when a webhook request is received").
  4. Name the webhook and click **Create** / **Copy**.

### 4. Atlassian Opsgenie (`OpsgenieAdapter`)
- **Required Variables**: `OPSGENIE_API_KEY`, `OPSGENIE_ENDPOINT`
- **Standard Public Endpoints**:
  - US: `https://api.opsgenie.com/v2/alerts`
  - EU: `https://api.eu.opsgenie.com/v2/alerts`
- **How to Obtain**:
  1. In Opsgenie, navigate to **Settings** -> **Integration list**.
  2. Select **API** integration (or **Default API**).
  3. Copy the generated **API Key** (`GenieKey`).

### 5. Generic Webhook (`WebhookAdapter`)
- **Required Variable**: `GENERIC_WEBHOOK_URL`
- **How to Obtain**:
  - Point to any internal or third-party HTTP gateway accepting JSON POST requests (e.g., an internal dispatch gateway, AWS API Gateway, or custom microservice).

### 6. Discord (`DiscordAdapter`)
- **Required Variable**: `DISCORD_WEBHOOK_URL`
- **How to Obtain**:
  1. Open Discord, click the gear icon next to your target channel (**Edit Channel**).
  2. Select **Integrations** -> **Webhooks** -> **New Webhook**.
  3. Copy the Webhook URL (format: `https://discord.com/api/webhooks/{id}/{token}`).

### 7. Telegram (`TelegramAdapter`)
- **Required Variables**: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `TELEGRAM_ENDPOINT_TEMPLATE`
- **Standard Endpoint Template**: `https://api.telegram.org/bot{bot_token}/sendMessage`
- **How to Obtain**:
  1. Open Telegram and message `@BotFather`.
  2. Send `/newbot`, follow prompts, and receive the HTTP API token (`TELEGRAM_BOT_TOKEN`).
  3. Add the bot to your group or channel. Send a message in the group.
  4. Query `https://api.telegram.org/bot<TOKEN>/getUpdates` to read the group's `chat.id` (`TELEGRAM_CHAT_ID`).

### 8. Splunk / VictorOps (`VictorOpsAdapter`)
- **Required Variable**: `VICTOROPS_ROUTING_URL`
- **How to Obtain**:
  1. In VictorOps / Splunk On-Call, navigate to **Settings** -> **Integrations** -> **REST Endpoint**.
  2. Enable the endpoint and copy the Post URL (format: `https://alert.victorops.com/integrations/generic/20131114/alert/{api_key}/{routing_key}`).

### 9. Datadog (`DatadogAdapter`)
- **Required Variables**: `DATADOG_API_KEY`, `DATADOG_ENDPOINT`
- **Standard Public Endpoints**:
  - US1: `https://api.datadoghq.com/api/v1/events`
  - US5: `https://api.us5.datadoghq.com/api/v1/events`
  - EU1: `https://api.datadoghq.eu/api/v1/events`
- **How to Obtain**:
  1. In Datadog, go to **Organization Settings** -> **API Keys**.
  2. Generate or copy an API Key.

### 10. New Relic (`NewRelicAdapter`)
- **Required Variables**: `NEW_RELIC_INSERT_KEY`, `NEW_RELIC_ENDPOINT`
- **Standard Public Endpoints**:
  - US: `https://insights-collector.newrelic.com/v1/accounts/{account_id}/events`
  - EU: `https://insights-collector.eu01.nr-data.net/v1/accounts/{account_id}/events`
- **How to Obtain**:
  1. In New Relic, navigate to **API Keys**.
  2. Create or copy an **Ingest - License** or **Insights Insert Key**.

### 11. Grafana OnCall (`GrafanaOnCallAdapter`)
- **Required Variable**: `GRAFANA_ONCALL_WEBHOOK_URL`
- **How to Obtain**:
  1. In Grafana, open **OnCall** -> **Integrations**.
  2. Click **New integration** -> choose **Webhook**.
  3. Copy the unique integration HTTP POST URL.

### 12. Mattermost (`MattermostAdapter`)
- **Required Variable**: `MATTERMOST_WEBHOOK_URL`
- **How to Obtain**:
  1. In Mattermost, go to **Main Menu** -> **Integrations** -> **Incoming Webhooks**.
  2. Click **Add Incoming Webhook**, choose channel and name.
  3. Copy the URL (format: `https://mattermost.yourdomain.com/hooks/...`).

### 13. Cisco Webex (`WebexAdapter`)
- **Required Variables**: `WEBEX_BOT_TOKEN`, `WEBEX_ROOM_ID`, `WEBEX_ENDPOINT`
- **Standard Public Endpoint**: `https://webexapis.com/v1/messages`
- **How to Obtain**:
  1. Go to [developer.webex.com](https://developer.webex.com/) -> **My Apps** -> **Create a Bot**.
  2. Copy the **Bot Access Token**.
  3. Add the bot to your Webex Space. Query the Webex rooms API to retrieve the `roomId`.

### 14. Twilio SMS (`TwilioSmsAdapter`)
- **Required Variables**: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`, `TWILIO_ENDPOINT_TEMPLATE`
- **Standard Endpoint Template**: `https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json`
- **How to Obtain**:
  1. Sign in to the [Twilio Console](https://console.twilio.com/).
  2. On the dashboard, locate **Account SID** and **Auth Token**.
  3. Under **Phone Numbers** -> **Manage** -> **Active numbers**, copy an SMS-enabled number (`from_number`).

### 15. Email SMTP (`EmailSmtpAdapter`)
- **Required Variables**: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`
- **How to Obtain**:
  - Obtain SMTP relay credentials from your enterprise mail server, SendGrid, Amazon SES, Google Workspace, or Mailgun (e.g., `smtp.sendgrid.net:587`).

---

## Decision Summary
- Zero URLs or API keys are hardcoded in application logic.
- All configurations are bound via environment variables and declared across `config/env.schema`, Helm `values.yaml`, Kubernetes `configmap.yaml`, and Docker Compose.
