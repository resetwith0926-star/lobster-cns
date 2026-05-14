# Lobster CNS System Manifest

## Mission

Lobster CNS is the central AI CEO brain for ResetWith/CNFCD.

## Current Scope

Version `v0.1.2` supports task creation, CEO task review, DeepSeek-powered decision-making, structured CEO decision output, memory, event logs, LLM call logs, and local dashboard visibility.

## Non-Goals

This version does not include social media integrations, Telegram bots, n8n integrations, auto-posting, real worker agents, browser automation, scraping, messaging, commenting, or platform control.

## Authority Model

The human owner is the final authority. CEOAgent can recommend, but cannot execute external actions.

## Safety Rules

No external action may happen without human approval. Secrets must not be displayed in logs or dashboards. Disabled agents cannot execute tasks. All future platform agents are simulation-only placeholders.

## Success Definition

The system is successful when a task can be created, reviewed by CEOAgent, stored, logged, and viewed in the dashboard.
