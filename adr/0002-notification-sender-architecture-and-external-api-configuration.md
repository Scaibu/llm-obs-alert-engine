# ADR 0002: Notification Sender Architecture and External Integration Configuration

## Status
Accepted

## Context
The `alert-engine` dispatches critical incident notifications to external platforms including Slack and PagerDuty. Previously:
1. Adapters resided in separate folders (`adapters/slack`, `adapters/pagerduty`) rather than a unified notification sender module.
2. Endpoint URLs and routing credentials had hardcoded fallbacks in configuration instead of requiring explicit declaration in environment variables or deployment manifests.
3. Notification sender settings (such as request timeouts and custom endpoints) lacked first-class configuration.

### Cross-Check: Slack Webhook vs Web API (`chat.postMessage`)
According to official Slack API specifications:
- **Incoming Webhooks (`https://hooks.slack.com/services/...`)**: Each modern Slack App incoming webhook is permanently pinned to a single designated channel chosen during installation. The payload parameter `"channel"` is ignored by modern Slack incoming webhooks.
- **Dynamic Channel & DM Delivery (`chat.postMessage`)**: When dynamic channel routing (e.g., `#llm-cost-alerts` vs `#llm-safety-alerts`) or user direct messages (e.g., `@user_id`) are required from a single credential, Slack requires the Web API endpoint `https://slack.com/api/chat.postMessage` using a Bot User OAuth Token (`xoxb-...`) with `chat:write` scope.
- **Webhook Gateway / Reverse Proxy**: Alternatively, organizations deploy an internal notification router/webhook gateway (e.g. `slack-sink.llmobs.internal` or an AWS Lambda/Cloud Function webhook forwarder) that reads the `"channel"` field from the payload and forwards the message to Slack via Bot Token.

### Cross-Check: PagerDuty Events API v2
According to official PagerDuty API specifications:
- **Endpoint**: `https://events.pagerduty.com/v2/enqueue`
- **Authentication**: Uses a 32-character hexadecimal Integration Key passed in the payload as `routing_key`.
- **Key Generation**:
  - In PagerDuty UI: **Services** -> **Service Directory** -> Select Service -> **Integrations** tab -> **Add integration** -> Select **Events API v2** -> Copy **Integration Key**.
  - Via PagerDuty REST API: `POST https://api.pagerduty.com/services/{service_id}/integrations` with integration type `events_api_v2_inbound_integration`.
- **Payload Schema**:
  - `routing_key`: Integration Key for the service.
  - `event_action`: `trigger`, `acknowledge`, or `resolve`.
  - `dedup_key`: Unique string used for incident grouping and deduplication.
  - `payload`: Contains `summary`, `severity` (`info`, `warning`, `error`, `critical`), and `custom_details`.

## Decision
1. **Consolidated Notification Adapters (`src/adapters/notification_senders/`)**:
   Standardized 15 enterprise and community notification/incident management adapters:
   - **Slack** (`SlackAdapter`): Webhook / internal gateway dispatcher.
   - **PagerDuty** (`PagerDutyAdapter`): Events API v2 incident trigger and resolve.
   - **Microsoft Teams** (`TeamsAdapter`): Office 365 / Adaptive Cards webhook.
   - **Opsgenie** (`OpsgenieAdapter`): Atlassian Opsgenie Alert API with alias closing.
   - **Generic Webhook** (`WebhookAdapter`): Custom HTTP JSON event webhook.
   - **Discord** (`DiscordAdapter`): Discord Channel Webhook API.
   - **Telegram** (`TelegramAdapter`): Bot API `sendMessage`.
   - **VictorOps / Splunk On-Call** (`VictorOpsAdapter`): REST incident integration.
   - **Datadog** (`DatadogAdapter`): Datadog Events API (`/api/v1/events`).
   - **New Relic** (`NewRelicAdapter`): Insights Collector API.
   - **Grafana OnCall** (`GrafanaOnCallAdapter`): Alert webhook integration.
   - **Mattermost** (`MattermostAdapter`): Incoming Webhook API.
   - **Cisco Webex** (`WebexAdapter`): Webex Messages API (`/v1/messages`).
   - **Twilio SMS** (`TwilioSmsAdapter`): Twilio Programmable SMS API.
   - **Email SMTP** (`EmailSmtpAdapter`): Direct TLS/STARTTLS SMTP dispatch.

2. **Environment Variable Configuration (Zero Hardcoded Secrets)**:
   Credentials, endpoints, and tokens are passed via environment variables (without hardcoded defaults):
   - Slack: `SLACK_WEBHOOK_URL`, `SLACK_TIMEOUT_SECONDS`
   - PagerDuty: `PAGERDUTY_ROUTING_KEY`, `PAGERDUTY_ENDPOINT`, `PAGERDUTY_TIMEOUT_SECONDS`
   - Teams: `TEAMS_WEBHOOK_URL`
   - Opsgenie: `OPSGENIE_API_KEY`, `OPSGENIE_ENDPOINT`
   - Generic Webhook: `GENERIC_WEBHOOK_URL`
   - Discord: `DISCORD_WEBHOOK_URL`
   - Telegram: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
   - VictorOps: `VICTOROPS_ROUTING_URL`
   - Datadog: `DATADOG_API_KEY`, `DATADOG_SITE`
   - New Relic: `NEW_RELIC_ACCOUNT_ID`, `NEW_RELIC_INSERT_KEY`
   - Grafana OnCall: `GRAFANA_ONCALL_WEBHOOK_URL`
   - Mattermost: `MATTERMOST_WEBHOOK_URL`
   - Cisco Webex: `WEBEX_BOT_TOKEN`, `WEBEX_ROOM_ID`
   - Twilio: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`
   - Email: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`

## Consequences
- Clean modular organization under `src/adapters/notification_senders/`.
- No sensitive credentials or fixed webhook endpoints hardcoded in source code or default configuration.
- Operators can switch between public endpoints and internal enterprise proxies via environment variables without code modification.
