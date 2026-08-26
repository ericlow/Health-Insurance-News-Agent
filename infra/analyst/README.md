# AnalystAgent — Deployment

The AnalystAgent handles Discord `/analysis` slash commands. This directory holds
the Terraform for its public HTTP endpoint.

## Architecture

```
Discord  →  API Gateway (HTTP API)  →  Lambda: analyst-handler (Lambda A)
                                          └─ async self-invocation  →  analyst-handler (Lambda B / engine mode)
                                                                          └─ Claude tool-loop → Neon → Discord PATCH
```

**Lambda A** (Discord gateway): verifies signature, returns type 5 deferred, invokes itself async.
**Lambda B** (engine): same function, detected by `{"mode": "engine"}` in the event payload.
**Why API Gateway and not a Lambda Function URL:** this AWS account blocks public
Lambda Function URLs — they return 403 from AWS's auth layer even with `auth-type
NONE` and a public resource policy. API Gateway is the public entrance instead.

## Components

| Piece | What | Managed by |
|---|---|---|
| Lambda `analyst-handler` | Handler `agent.analyst.interactions.handler`, python3.12 / x86_64 | Console + CLI (not yet in Terraform) |
| API Gateway HTTP API | Public endpoint, `POST /` → Lambda proxy | Terraform (this dir) |
| Discord app `AgentAnalyst` | Slash command + interactions endpoint | Discord Developer Portal |
| Neon DB | `a2_conversations` table — conversation state | `db/schema.sql` |
| Endpoint URL | `https://6scddpumv6.execute-api.us-west-1.amazonaws.com/` | Terraform output |

## One-time setup (after AGE-95)

### 1. Apply the DB schema

```bash
psql $DATABASE_URL -f db/schema.sql
```

### 2. Add env vars to the Lambda

```bash
source .env
aws lambda update-function-configuration --function-name analyst-handler \
  --environment "Variables={
    DISCORD_PUBLIC_KEY=$DISCORD_PUBLIC_KEY,
    DISCORD_APPLICATION_ID=$DISCORD_APPLICATION_ID,
    ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY,
    DATABASE_URL=$DATABASE_URL
  }" --region us-west-1
```

### 3. Allow the Lambda to invoke itself (self-invocation for engine mode)

In the AWS Console → IAM → Roles → find the `analyst-handler` execution role → add inline policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": "lambda:InvokeFunction",
    "Resource": "arn:aws:lambda:us-west-1:494883819786:function:analyst-handler"
  }]
}
```

## Deploy code changes

The engine adds dependencies (anthropic, psycopg2, BeautifulSoup, requests) that must be
bundled — they're not in the Lambda runtime. All need the Linux wheel since Lambda runs on
Amazon Linux.

```bash
rm -rf /tmp/analyst-build && mkdir -p /tmp/analyst-build

pip install --platform manylinux2014_x86_64 --implementation cp --python-version 3.12 \
  --only-binary=:all: --target /tmp/analyst-build \
  PyNaCl anthropic psycopg2-binary requests beautifulsoup4 lxml

mkdir -p /tmp/analyst-build/agent/analyst
cp agent/__init__.py /tmp/analyst-build/agent/
cp agent/http_utils.py /tmp/analyst-build/agent/
cp agent/analyst/__init__.py \
   agent/analyst/interactions.py \
   agent/analyst/engine.py \
   /tmp/analyst-build/agent/analyst/

( cd /tmp/analyst-build && zip -r -q analyst.zip . -x "*.dist-info/*" )

aws lambda update-function-code --function-name analyst-handler \
  --zip-file fileb:///tmp/analyst-build/analyst.zip --region us-west-1
```

## Apply infra changes

```bash
export AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=...   # from .env
terraform -chdir=infra/analyst init
terraform -chdir=infra/analyst plan
terraform -chdir=infra/analyst apply
```

Requires the `analyst-apigateway` inline policy on the `github-actions-deploy` IAM
user (apigateway:* + lambda:AddPermission/GetPolicy/RemovePermission). State is
local and gitignored.

## Register / update the slash command

```bash
python3 -c "from dotenv import load_dotenv; load_dotenv(); \
  from agent.analyst.register_commands import register; register()"
```

Needs `DISCORD_APPLICATION_ID`, `DISCORD_BOT_TOKEN`, `DISCORD_GUILD_ID` in `.env`.
Guild registration is instant; drop `DISCORD_GUILD_ID` for global (~1h propagation).

## Discord endpoint

If the endpoint URL changes (new `terraform apply` from scratch), update it in the
Discord Developer Portal → AgentAnalyst → General Information → **Interactions
Endpoint URL**. Discord verifies it with a signed PING on save.
