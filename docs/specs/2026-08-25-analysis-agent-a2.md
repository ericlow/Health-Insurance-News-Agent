# Analysis Agent A2 — Feature Spec

_Status: draft — pending Eric review 2026-08-26_
_Last updated: 2026-08-25_

---

## Background

AGE-71 (CalOptima OC entry analysis) revealed that analyst Matt missed SB 260's alternate-default pathway in his first two drafts — a 2019 statute that generates no recent headlines and appears in no dataset. The miss was caught only because Matt reviewed his own work a third time. The goal of A2 is to let Matt trigger structured analysis on demand, without having to do the full research loop himself.

V1 is intentionally minimal: one tool (fetch the article), Claude reasoning, Discord response. The toolset expands in subsequent iterations once the end-to-end flow is verified working.

Full design context: `docs/a2/prd.md`, `docs/a2/trd.md`, `docs/a2/Aug_24_agent_discussion.md`, `docs/a2/live-simulation-aug24.md`.

---

## User Story

As Matt (Elevance account analyst), I want to paste a news article URL into Discord and ask "how does this affect Anthem?" so that I get a structured analysis without doing the research loop myself.

---

## Acceptance Criteria

1. Matt can trigger a new analysis with `/analysis <url> <question>`
2. Discord shows a thinking spinner within 3 seconds
3. The agent fetches the article, runs analysis, and posts findings inline — including a conversation ID
4. Matt can continue the conversation with `/analysis <id> <follow-up>`
5. The agent loads full prior history and responds in context
6. If the URL is unreachable, the agent attempts analysis from URL + question alone and notes the failure

---

## Technical Design

### Data Model

```yaml
table: a2_conversations
columns:
  id:         SERIAL PRIMARY KEY
  url:        TEXT NOT NULL
  question:   TEXT NOT NULL
  messages:   JSONB NOT NULL DEFAULT '[]'   # full Claude messages array
  created_at: TIMESTAMPTZ NOT NULL DEFAULT now()
  updated_at: TIMESTAMPTZ NOT NULL DEFAULT now()
```

### Execution Model

```
Matt: /analysis <url> <question>
  → Discord API Gateway → Lambda A
      Lambda A: verify signature, return {type: 5}, invoke Lambda B async
  → Lambda B: fetch URL, run Claude, post to Discord via interaction follow-up
      save conversation to Neon (id, url, question, messages)
  → Matt sees analysis + "Conversation ID: 42"

Matt: /analysis 42 <follow-up>
  → Lambda A: verify signature, return {type: 5}, invoke Lambda B async (conversation_id=42)
  → Lambda B: load messages from Neon, append follow-up, run Claude, post to Discord
      save updated messages to Neon
```

### Discord Interaction Contract

- Lambda A receives Discord interaction POST via API Gateway
- Signature verification: Ed25519 using `DISCORD_PUBLIC_KEY` env var
- Ping response (type 1): `{"type": 1}`
- Slash command response (type 2): `{"type": 5}` (deferred — shows thinking spinner)
- Lambda B posts result via: `PATCH https://discord.com/api/webhooks/{DISCORD_APPLICATION_ID}/{interaction_token}/messages/@original`

### Command Parsing

| Input shape | Behavior |
|---|---|
| `/analysis <url> <text>` | New analysis — first token starts with `http` |
| `/analysis <integer> <text>` | Continuation — first token is a whole number |
| Anything else | Error: post usage instructions to Discord |

### Environment Variables

| Variable | Purpose |
|---|---|
| `DISCORD_APPLICATION_ID` | Constructs follow-up webhook URL |
| `DISCORD_PUBLIC_KEY` | Ed25519 signature verification |
| `ANTHROPIC_API_KEY` | Claude API |
| `DATABASE_URL` | Neon connection (existing) |

---

## Behavioral Specs (Gherkin)

### New analysis

```gherkin
Scenario: Matt triggers a new analysis
  Given Matt types /analysis https://example.com/article "how does this affect Anthem?"
  When Lambda A receives the Discord interaction
  Then Lambda A returns {type: 5} within 3 seconds
  And Lambda B fetches the article URL
  And Lambda B runs Claude with the article content and Matt's question
  And Lambda B posts the analysis inline to the Discord channel
  And the response includes "Conversation ID: <integer>"
  And the conversation is saved to a2_conversations with the messages array

Scenario: URL is unreachable (403 or timeout)
  Given Matt types /analysis https://blocked.com/article "how does this affect Anthem?"
  When Lambda B fetches the URL and receives a 403 or timeout
  Then Lambda B posts analysis based on URL and question context alone
  And the response notes that the article body could not be fetched
  And the response still includes a Conversation ID
  And the conversation is saved to a2_conversations
```

### Follow-up

```gherkin
Scenario: Matt asks a follow-up question
  Given conversation 42 exists in a2_conversations with prior messages
  When Matt types /analysis 42 "what about the MA book specifically?"
  Then Lambda A returns {type: 5} within 3 seconds
  And Lambda B loads conversation 42 from Neon
  And Lambda B appends Matt's follow-up to the message history
  And Lambda B runs Claude with the full conversation history
  And Lambda B posts the updated analysis inline to Discord
  And the updated messages array is saved to a2_conversations

Scenario: Invalid conversation ID
  Given conversation 99999 does not exist in a2_conversations
  When Matt types /analysis 99999 "follow-up question"
  Then Lambda B posts "No conversation found with ID 99999"
  And no new conversation is created
```

---

## Decisions

| Question | Decision | Rationale |
|---|---|---|
| Tool set | One tool: fetch URL only | Start minimal; validate end-to-end before expanding |
| Conversation ID | Integer (SERIAL primary key) | Simple, no nickname machinery needed |
| Discord response location | Inline same channel | Threads add complexity; not needed for V1 |
| Discord ack | Thinking spinner only (type 5) | No text ack; Lambda B posts all content |
| URL fetch failure | Attempt analysis with URL+question context, note error inline | Better than hard stop; Claude can still reason from headline/URL |
| Finalize step | Deferred to V2 | No clean consolidated artifact in V1 |
| Conversation retrieval for follow-up | Integer ID only — Matt provides it | No vector search or nickname lookup in V1 |

---

## Out of Scope (V1)

- Human-readable nicknames for conversations
- Vector search / fuzzy conversation retrieval
- `lookup_regulatory_rules`, `search_web`, `search_articles` tools
- Finalize step (clean consolidated artifact)
- Discord threads
- Article embeddings (Voyage AI)
- Backfill of existing articles

---

## Libraries

| Library | Version | Purpose |
|---|---|---|
| `PyNaCl` | `1.5.0` | Discord Ed25519 signature verification |
| `anthropic` | current installed | Claude API |
| `psycopg2-binary` | current installed | Neon connection |
| `requests` | current installed | URL fetch |
