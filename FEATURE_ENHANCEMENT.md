# Feature Enhancement Backlog

This document captures post-MVP ideas. Revisit once core flows (chat, exports, alerts) are validated in production-like usage.

## Authentication & Sessions
- **Refresh token UX polish**: background refresh with toast when session expires.
- **Role-based access**: different presets or quotas per user role.
- **Audit log feed**: expose recent sign-ins and critical actions in admin panel.

## Conversations Experience
- **Pinned conversations**: surface high-priority chats at top of history.
- **Advanced search**: filter conversations by keyword, date, or tag.
- **Realtime sync**: subscribe to Supabase changes to reflect updates across tabs.

## Marketing Workflows
- **Segment library**: save preset parameter configurations for quick reuse.
- **Batch exports queue**: trigger async export generation for large datasets and email link when ready.
- **Insights dashboard**: charts for market metrics (volume, PSF trend) per community.

## Alerts & Automation
- **Alert schedules**: allow weekly/daily cadence and pause/resume toggles.
- **Tagging & campaigns**: group alerts into outreach campaigns with shared notes.
- **Delivery integrations**: webhook or Slack notifications in addition to email/SMS.

## UX & Telemetry
- **Analytics events**: send structured telemetry (preset run, alert create) to backend `/events` endpoint.
- **Dark mode**: toggle via CSS variables; respect system preference.
- **Onboarding tips**: guided tour highlighting chat, exports, alerts.

## Infrastructure & Ops
- **Rate limiting per user**: configurable request quotas to protect backend.
- **Health dashboards**: include alerts/export success metrics in Grafana/Prometheus.
- **Secrets management**: migrate Supabase keys to managed secret store (e.g., Vault, AWS Secrets Manager).
