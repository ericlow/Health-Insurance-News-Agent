# Domain Expert Inputs

---

## 2026-06-19

We are looking for major changes in relationships. Could be the form of acquisitions, mergers, partnerships, divestitures, or terminations of deals between major insurance carriers and providers.

Time frame would be last five years; shorter is also fine.

What I need to do for the agent is figure out how to give it a goal once it finds something. Right now, I'm thinking: define geographic regions impacted, size the entities involved economically, and perhaps do research on alternatives.

In essence, the agent that we are building will prompt other agents.

**Example — CalPERS/United/Sutter:**

CalPERS prepares to drop United Healthcare. ~90k members shifting from United to Sutter. Sutter is not a full-blown insurance carrier. Anthem is actually the third party that processed the claims — so Anthem also wins. And Sutter needs to fill out the network and they are using Anthem's network to do that — another win for Anthem.

Two telltale signs this was coming: (1) CalPERS said they want to kick out United and opened a soft RFP. (2) United laid off the CalPERS sales team a month ago.

In this case, this is huge news, but not necessarily my rodeo. What I would want to show is how much volume was picked up via Sutter.

References:
- https://newsroom.cigna.com/uc-health
- https://www.yahoo.com/healthcare/articles/calpers-prepares-drop-united-healthcare-000333348.html

---

## 2026-06-20

Build in two phases:

1. First build the system that pulls news items from the source and saves them to the database.
2. Then design the prompts that analyze and triage the saved articles — to extract details, determine if they are financial or not, etc.

We care about three types of substantive stories: (1) relationship changes, (2) business changes, and (3) financial implications. The triage filter should discard generic PR content and soft qualitative stories — both types are noise. Stories need to be about actual relationships, business events, or financial impact to be worth analyzing further.

All articles sourced from newsroom.cigna.com are public information — no data privacy constraints on tooling choices.

Use Braintrust for prompt testing and evaluation. Articles are public so there is no concern with sending them to a commercial platform.

## 2026-07-10

Another input
https://med.stanford.edu/news/all-news/2021/02/stanford-medicine-and-sutter-health-to-provide-east-bay-cancer-care.html

## 2026-07-11

**Short list of entities to watch:**

Insurers: United Healthcare, Blue Shield, Anthem / Blue Cross, Aetna, Cigna, Healthnet / Centene, Kaiser

Hospitals / doctors: Sutter Health, Stanford, UC, Cedars, Providence, Optumcare, Heritage, Scripps, Sharp, Kaiser

Employers: CalPERS, nursing unions, doctors unions, labor unions for major employers

California Health and Human Services open data portal: https://data.chhs.ca.gov/
