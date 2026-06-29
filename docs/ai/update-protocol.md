# Agent Context Update Protocol

Philalens is designed to be maintainable by future AI agents. Context updates
are part of the work, not optional cleanup.

## When To Update Context

Update durable context when a change affects any of these areas:

- product behavior or user workflow
- architecture or component boundaries
- data model or storage approach
- dependencies, setup, or developer workflow
- AI prompts, model usage, or evaluation strategy
- catalog, market data, or licensing strategy
- roadmap, priorities, or known risks
- agent workflow or repository conventions

## What To Update

Use this mapping:

- Product behavior changed: update `docs/product-brief.md`, `README.md`, or both.
- Product workflow changed: update `docs/product-workflow.md`.
- Architecture changed: update `docs/architecture.md`.
- Data source or valuation strategy changed: update `docs/data-strategy.md`.
- Research or source assumptions changed: update the relevant file under
  `docs/research/`.
- Priority or milestone changed: update `docs/roadmap.md`.
- Durable decision made: add an entry to `docs/ai/decisions.md`.
- Current project memory changed: update `docs/ai/context.md`.
- End of a work session: update `docs/ai/session-handoff.md`.
- Agent workflow changed: update `AGENTS.md` and any relevant adapter files.

## Required End-of-Session Checklist

Before finishing a meaningful change:

1. Run relevant tests or smoke checks.
2. Review `git diff --name-only`.
3. Update context docs if any changed file affects project understanding.
4. Run `python3 scripts/check_agent_context.py --base HEAD~1 --head HEAD` after
   committing, or run it against an appropriate base before opening a PR.
5. Leave `docs/ai/session-handoff.md` accurate for the next agent.

## Context Quality Standard

Context updates should be concise and factual. A future agent should be able to
answer these questions without reading chat history:

- What is Philalens trying to build?
- What exists today?
- What is not implemented yet?
- What decisions are already made?
- What risks or constraints matter?
- What should happen next?
