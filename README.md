# עברית היום — Daily Hebrew Reading

A static daily magazine for learners reading modern spoken Israeli Hebrew. Each new issue combines sourced CURRENT stories, realistic EVERYDAY situations, natural DIALOG conversations, sourced HISTORY stories, and one grouped SHORTS page at configurable reading levels. Almost all Hebrew text is selectable for Russian or English translation.

The repository contains a complete sample issue, so the site can be built and tested without an OpenAI key. The production URL is expected to be `https://teomant.github.io/daily-hebrew-reading/`.

## What is included

- Static home, archive, day, and article pages in the selected “Jerusalem Journal” design.
- Configurable reading levels (`א`, `א+`, `ב` initially) and interface/translation locale registries (`ru`, `en` initially).
- Persisted reading level, translation language, and interface language preferences.
- Keyboard, hover, and tap translation popovers.
- Source links and optional externally hosted, attributed source images with graceful failure.
- Staged OpenAI Responses API generation: web-enabled CURRENT/HISTORY discovery returns compact screening records, strict duplicate review and deterministic selection choose publishable subjects, batched web-enabled requests deeply research only selected HISTORY stories, separate no-web planners create the full generated stories and SHORTS items, and adaptation handles each full story or short item independently with lexical units and contextual translations.
- A normal 2 CURRENT / 3 HISTORY / 3 EVERYDAY / 2 DIALOG / 1 SHORTS-page target mix. Generated material draws from three pools: essential situations such as healthcare or documents, ordinary routines such as shopping or transport, and experiences such as cooking or trips. The five full generated stories target a 2 / 2 / 1 mix across these pools; eleven planned SHORTS target 5 / 4 / 2. These are editorial targets, not publication gates. Each SHORTS item is a two-or-three-sentence mini-situation planned and adapted independently. Valid items are kept, fresh replacements are planned after failures, and any remaining valid items (up to eleven) are collected on one page. Missing sourced stories reduce the issue size instead of expanding the fixed generated allocation.
- An 18-candidate sourced discovery pool before filtering: up to six compact CURRENT and at least 12 compact HISTORY candidates. CURRENT stays within Israel on every pass, using local reporting, municipal updates, and relevant public-service announcements; nonlocal CURRENT candidates are rejected in review. The first two HISTORY attempts focus on Israeli material across varied reference, library, archive, cultural, municipal, educational, and biographical sources; a third attempt may search worldwide for remaining HISTORY slots. No HISTORY family or source collection has a fixed quota. The strongest surviving subjects are selected in editorial order; invalid or duplicate candidates are removed individually. Reviewed but unselected HISTORY candidates remain reserves, with Israeli candidates ahead of worldwide fallbacks.
- Safe same-day append behavior; existing stories are preserved, duplicates are rejected, and new entries are only EVERYDAY or DIALOG in any mix. The combined issue is reordered generated-first without changing story text.
- Content validation, tests, daily/manual GitHub Actions, and GitHub Pages deployment.

The full English product requirements are in [docs/product-specification.md](docs/product-specification.md). The earlier design choices remain available in [design-previews/README.md](design-previews/README.md).

## Local build

Python 3.12 or newer is recommended. Building and testing the sample requires no third-party packages:

```bash
python -m src.validate_content
python -m unittest discover -s tests -v
python -m src.build_site --base-path /
python -m http.server 8000 --directory dist
```

Open `http://localhost:8000/`. Omit `--base-path /` for the production GitHub Pages build.

Generation additionally requires the official OpenAI SDK:

```bash
python -m pip install -r requirements.txt
export OPENAI_API_KEY="..."
export OPENAI_MODEL="gpt-6-luna"
python -m src.generate_issue --date 2026-09-04
```

If that date does not exist, the generator creates a normal full issue. If it already exists, it appends three fully AI-generated EVERYDAY or DIALOG stories by default, in any mix and without web research:

```bash
python -m src.generate_issue --date 2026-09-04 --additional-stories 2
```

Generation validates completed content before replacing any repository files. Exhausted API/request failures, unusable planning or research, and invalid final combined content exit with an error and leave the published site unchanged. An individual adaptation that remains invalid after its retry is omitted instead, and later articles continue.

## Content and configuration

- `content/YYYY-MM-DD.json` — complete ordered issue.
- `content/index.json` — dates, story counts, and estimated reading times.
- `content/everyday-history.json` — EVERYDAY, DIALOG, and individual SHORTS scenario history used to reduce repetition.
- `config/site.json` — base path, enabled locales, defaults, flexible new-issue count range, and seven-day prompt lookback windows.
- `config/reading-levels.json` — ordered level IDs, wording guidance, and reading speeds.
- `i18n/*.json` — interface dictionaries. Adding a locale requires a matching dictionary and adding its code to `site.json`.
- `prompts/*.md` — sourced editorial, selected-HISTORY research, deduplication, everyday, dialogue, adaptation, and curated frequent-Hebrew guidance.

Old issues list their own available levels/locales and remain readable when new levels, locales, or story types are configured later. The validator rejects missing adaptations and requires at least 75% contextual translation coverage per story level and language; individual units may remain untranslated when no useful direct translation exists.

## GitHub setup

The repository owner needs to configure these once:

1. In **Settings → Pages**, keep **Source: GitHub Actions**. No custom or verified domain is required for the free `github.io` address.
2. In **Settings → Environments**, use the environment named `daily-hebrew-reading`.
3. In that environment, add secret `OPENAI_API_KEY`. The workflow pins every generation phase to `gpt-6-luna` at low reasoning effort; no GitHub `OPENAI_MODEL` variable is required.
4. Under **Settings → Actions → General → Workflow permissions**, allow **Read and write permissions** so the generator can commit `content/` to `master`.

The OpenAI API is billed separately from ChatGPT Plus. The API uses the credits on the API account; GitHub Pages is free for a public repository under GitHub's normal Pages/Actions quotas.

## Running the workflows

- **Generate daily issue v2** runs at `01:37 UTC` and can also be started from **Actions → Generate daily issue v2 → Run workflow**.
- Leave `date` blank to use the current UTC date. The workflow defaults `additional_stories` to `0`; if that issue already exists, it logs the trigger details and stops before setup or AI access. Enter a positive value to explicitly append that many EVERYDAY or DIALOG stories. The value is ignored when creating a new full issue.
- **Validate and deploy site** runs on an ordinary push to `master` and never calls OpenAI.

Generation logs timestamp each research, adaptation, validation, and write phase. Immediately before each OpenAI call, it logs the complete phase-specific system and user prompts. Sourced discovery has up to three attempts: CURRENT searches remain local throughout, while HISTORY has two Israel-focused passes and one final worldwide fallback. Selected HISTORY research is one batched web call in a normal run and continues in batches for unresolved reviewed reserve replacements; two consecutive request failures abort the run. Generated scenarios use three canonical topic pools; prompts vary the goal, interaction, and outcome, and retry requests account for retained pool counts. Cooking and trip stories qualify when they include an actual event or activity rather than only vague plans. These no-web fictional scenarios teach useful language without inventing current official rules, fees, deadlines, diagnoses, or entitlements. Prompt exclusions use the previous seven days, while older content remains stored. Adaptation runs one story or SHORTS item per request. DIALOG planning freezes two Hebrew speaker names; adaptation receives a literal eight-turn example, and code normalizes labels and colons before validation. DIALOG and SHORTS adaptations receive three prompt attempts. Failed SHORTS are replaced one at a time within an eleven-attempt budget; the page publishes with any valid items, and zero valid items do not block the rest of the issue. Remaining dialogue-style imperfections are warnings when the ordinary public content contract is still valid, rather than a reason to silently remove the dialogue.

The generation workflow first logs the GitHub event, schedule expression, workflow identity, SHA, run metadata, resolved date, and issue-existence decision. A default same-day repeat stops there. When generation is needed, repository validation and unit tests run before OpenAI, so code or fixture failures stop without API spend. After generation it validates the changed content again and builds the exact site that will be committed and deployed.

Discovery receives only the editorial screening prompt and does not create HISTORY story beats. After duplicate review and selection, the selected-HISTORY research prompt freezes 8–12 distinct factual beats and marks at least two defining facts required; a dramatic story arc is not mandatory. Source links are retained when trustworthy URLs are available, but missing or discarded links do not invalidate an otherwise usable HISTORY pack. Adaptation develops those facts instead of substituting a résumé, source summary, institutional promotion, or generic statement about importance or legacy. Every newly researched HISTORY level must report coverage of every required beat. Reading levels are distinguished by wording and grammar: Alef uses common concrete language and simple clauses, Alef Plus broadens everyday vocabulary and connectors, and Bet uses richer natural language and moderately more complex structures. The small [frequency-aware Hebrew reference](prompts/frequent-hebrew.md) is passed to every adaptation as a soft wording preference, not a whitelist or difficulty gate. Python does not classify words as too difficult and does not fail content based on level length. New adaptations receive missing terminal punctuation automatically; alphabetic separator units are repaired in code by reclassifying language-bearing units or reattaching clear Hebrew prefixes before validation. The finished Hebrew uses mostly one-to-three-word translation chunks with longer units reserved for indivisible expressions and names. Individual empty translations are allowed, but each story level must reach at least 75% coverage per language.

The generation workflow commits with the GitHub Actions bot, then deploys the already validated build. The generated commit does not need to trigger a second workflow.

## Security

The API key is read only by the generation job from its GitHub environment. It is never written to JSON, HTML, frontend JavaScript, or Git. `.env`, `.idea/`, `.venv/`, and generated `dist/` output are ignored.
