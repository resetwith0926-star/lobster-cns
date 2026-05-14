# Lobster CNS

Lobster CNS is a local-first AI Agent Central Nervous System for ResetWith/CNFCD. The product is designed to become an AI company brain, but `v0.1.2` only builds the CEO Governance Core.

## What v0.1.2 Does

- Creates admin tasks.
- Lets CEOAgent review tasks with DeepSeek.
- Validates structured CEO decisions.
- Stores tasks, memories, events, and LLM calls in SQLite.
- Shows activity in a simple local dashboard.
- Keeps future agents as disabled placeholders.

## What v0.1.2 Does Not Do

- No Facebook, Instagram, X, LINE, Telegram, or n8n integrations.
- No browser automation, scraping, posting, commenting, or messaging.
- No real worker agents.
- No vector database.
- No chatbot or health coach onboarding flow.
- No shell command execution from the dashboard.

## Architecture

```text
Admin / Owner
  -> Admin API / Local Dashboard
  -> CEOAgent
  -> DeepSeekLLMProvider
  -> Decision Contract
  -> TaskQueue / MemoryService / EventLog / AgentRegistry
  -> SQLite + Dashboard View
```

## Safety Model

The human owner is the final authority. CEOAgent can recommend, classify, prioritize, and record, but it cannot execute external actions. All platform agents are disabled simulation-only placeholders.

Secrets are not displayed in the dashboard. API keys are not logged. Admin API endpoints require the `X-Admin-Secret` header.

## Human Approval Model

Every CEO decision in `v0.1.2` must include:

```json
{
  "requires_human_approval": true,
  "simulation_only": true
}
```

CEOAgent can move tasks to `planned`, `waiting_approval`, or `failed`. Only admin can complete or cancel tasks.

## Install

```bash
cd lobster-cns
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configure

```bash
cp .env.example .env
```

Edit `.env`:

```text
APP_ENV=local
DATABASE_URL=sqlite:///./lobster_cns.db
ADMIN_SECRET=change-me
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=your-deepseek-api-key
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com
LLM_TIMEOUT_SECONDS=30
LLM_MAX_RETRIES=2
```

## Run Locally

```bash
source .venv/bin/activate
uvicorn app.main:app --reload
```

Open the dashboard:

[http://127.0.0.1:8000](http://127.0.0.1:8000)

## Create A Task

Using curl:

```bash
curl -X POST http://127.0.0.1:8000/tasks \
  -H "Content-Type: application/json" \
  -H "X-Admin-Secret: change-me" \
  -d '{
    "title": "ResetWith 下週內容方向",
    "description": "請 CEOAgent 根據 ResetWith/CNFCD 的品牌方向，規劃下週內容主題、優先級、適合交給哪個未來 agent，並列出成功標準。"
  }'
```

You can also create a task from `/dashboard/tasks`.

## Review A Task With CEOAgent

```bash
curl -X POST http://127.0.0.1:8000/tasks/1/review \
  -H "X-Admin-Secret: change-me"
```

You can also open the task detail page and click `Review with CEOAgent`.

## Example Task Input

Title:

```text
ResetWith 下週內容方向
```

Description:

```text
請 CEOAgent 根據 ResetWith/CNFCD 的品牌方向，規劃下週內容主題、優先級、適合交給哪個未來 agent，並列出成功標準。
```

## Example CEO Decision Output

```json
{
  "contract_version": "ceo_decision.v1",
  "task_type": "content",
  "priority": "high",
  "risk_level": "low",
  "suggested_agent_role": "content_agent",
  "task_summary": "Plan next week's ResetWith content direction.",
  "ceo_decision": "Create a planning brief and wait for owner approval before publishing.",
  "reasoning_summary": "This is content strategy and should remain planning-only.",
  "recommended_steps": [
    "Review brand memory",
    "Draft weekly themes",
    "Ask owner to approve before execution"
  ],
  "requires_human_approval": true,
  "recommended_next_status": "waiting_approval",
  "blocked_by": [],
  "success_criteria": [
    "Task is classified",
    "Next steps are clear",
    "Owner can approve the next action"
  ],
  "estimated_complexity": "medium",
  "simulation_only": true,
  "memory_to_save": []
}
```

## Dashboard Pages

- `/` system overview
- `/dashboard/tasks` task board
- `/dashboard/tasks/{task_id}` task detail
- `/dashboard/agents` placeholder agent registry
- `/dashboard/events` event logs
- `/dashboard/memory` memory records
- `/dashboard/llm-calls` LLM call logs

## Run Tests

```bash
pytest
```

## Future Roadmap

- `v0.2`: stronger CEO planning and review workflows.
- `v0.3`: content agent as a disabled simulation first.
- `v0.4`: approval workflow before any external action.
- Later versions may add platform agents, but only after explicit human approval gates and safety reviews.

