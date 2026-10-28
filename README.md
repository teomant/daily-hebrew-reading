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
- An 18-candidate sourced discovery pool before filtering: up to six compact CURRENT and at least 12 compact HISTORY candidates. CURRENT stays within Israel on every pass, using local reporting, municipal updates, and relevant public-service announcements; nonlocal CURRENT candidates are rejected in review. The first two HISTORY attempts focus on Israeli material across varied reference, library, archive, cultural, municipal, educational, and biographical sources; a third attempt may search Jewish history and culture outside Israel for remaining HISTORY slots. Every HISTORY brief must establish an explicit Israeli or Jewish connection. No HISTORY family or source collection has a fixed quota. The strongest surviving subjects are selected in editorial order; invalid or duplicate candidates are removed individually. Reviewed but unselected HISTORY candidates remain reserves, with Israeli candidates ahead of worldwide fallbacks.
- Safe same-day append behavior; existing stories are preserved, duplicates are rejected, and new entries are only EVERYDAY or DIALOG in any mix. The combined issue is reordered generated-first without changing story text.
- Content validation, tests, daily/manual GitHub Actions, and GitHub Pages deployment.

HISTORY discovery and research both receive the concrete [source guide](prompts/history-sources.md): collection URLs, search routes, evidence priorities, and observed access limitations. It prioritizes curated collections, documented original material, and scholarly context; useful explanations of everyday life and memorable supported details outrank generic biographies. MUZA, the Israel Film Archive, Project Ben-Yehuda, Posen, and NLI collections provide specific starting points. Wikipedia remains an orientation/reference route and NLI blog posts remain useful supplementary leads. Collection URLs guide navigation; only consulted content pages become citations. These are editorial priorities, not publisher quotas or new source-count gates. No additional model calls are introduced.

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

Future articles target beginner Alef after alphabet decoding, with familiar words, explicit subjects, and one simple clause per sentence.
Alef HISTORY and EVERYDAY may use 2–4 short paragraphs; harder versions normally use 4–5 developed paragraphs.
Alef Plus connects familiar ideas, while Bet uses richer conversational language.
The [wording reference](prompts/frequent-hebrew.md) includes short calibration examples.
Difficulty remains a writing judgment, without a numeric vocabulary gate.
New dialogue structure and lexical segmentation receive local checks and bounded repairs.
Usable imperfect articles remain publishable with quality warnings, and archived issues remain readable.

## Content and configuration

- `content/YYYY-MM-DD.json` — complete ordered issue.
- `content/index.json` — dates, story counts, and estimated reading times.
- `content/everyday-history.json` — EVERYDAY, DIALOG, and individual SHORTS scenario history used to reduce repetition.
- `config/site.json` — base path, enabled locales, defaults, flexible new-issue count range, and prompt lookback windows: fourteen days for HISTORY, seven for CURRENT and generated scenarios.
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

Generation logs timestamp each phase and print its complete system and user prompts safely.
Sourced discovery has up to three attempts: CURRENT remains local, while HISTORY has two Israel-focused passes and one Jewish-history fallback.
Selected HISTORY research normally uses one batched call; two consecutive research request failures abort generation.
Generated scenarios keep the existing topic pools and targets.
Fresh `everydayMeta.storyPattern` metadata records a compact English goal, relationship, interaction, and outcome.
Recent and same-day context includes those patterns and individual SHORTS briefs so planners can compare plots across domains.
HISTORY excludes fourteen days of recent subjects; CURRENT and generated scenarios use seven days.
Older stored content without pattern metadata remains supported.

Adaptation runs one story or SHORTS item at a time.
Valid levels are retained; only unresolved levels are requested again within the existing two-attempt limit, or three for DIALOG and SHORTS.
DIALOG planning identifies exactly two speakers and their roles in the brief.
Code can restore a colon after an unambiguous separate name unit, but never assigns identities by paragraph position.
Unknown labels, nonalternating turns, and detectable third-person narration receive correction attempts.
After retries, retain the latest usable level with a warning if public structure, translation coverage, identity, and required factual coverage pass.
Only failures of those core contracts omit the article or item.
Semantic role consistency and reading-level fit still require observation of future output.

Local generation checks flag oversized units and whole multiword sentence targets, including punctuation stored separately.
One additional no-web annotation repair is allowed per story or SHORTS item, containing only affected groups and their Hebrew context.
Repair must preserve the rendered Hebrew exactly and produce valid contextual translations.
Invalid or failed annotation repair preserves the original usable article and logs the remaining quality defect.
SHORTS retain the existing eleven replacement-cycle limit and publish any valid items up to eleven.
No unconditional AI review stage or extra research stage is added.

Each API response logs input, cached-input, output, reasoning, and web-search counts with an estimated USD cost.
Reasoning tokens are included in output tokens and are not charged twice in the estimate.
A run summary is emitted on success, empty output, or failure, with observed subtotals and unknown/unpriced request counts.
`src/generation_usage.py` uses [standard Luna rates](https://developers.openai.com/api/docs/pricing) checked on October 28, 2026, including long-context multipliers and web-search calls.
Requests explicitly select the standard `default` service tier.
Unknown models, unsupported tiers, and missing usage produce unavailable estimates rather than guessed costs.
Estimates exclude unreported cache writes and SDK-internal retry usage; OpenAI billing is authoritative.
Logs contain no credentials through usage tracking, and no usage data is published in article JSON.

The generation workflow first logs the GitHub event, schedule expression, workflow identity, SHA, run metadata, resolved date, and issue-existence decision. A default same-day repeat stops there. When generation is needed, repository validation and unit tests run before OpenAI, so code or fixture failures stop without API spend. After generation it validates the changed content again and builds the exact site that will be committed and deployed.

Discovery receives only the editorial screening prompt and does not create HISTORY story beats. After duplicate review and selection, the selected-HISTORY research prompt freezes 8–12 distinct factual beats and marks at least two defining facts required; a dramatic story arc is not mandatory. Source links are retained when trustworthy URLs are available, but missing or discarded links do not invalidate an otherwise usable HISTORY pack. Adaptation develops those facts instead of substituting a résumé, source summary, institutional promotion, or generic statement about importance or legacy. Every newly researched HISTORY level must report coverage of every required beat. Reading levels are distinguished by wording and grammar: Alef uses common concrete language and simple clauses, Alef Plus broadens everyday vocabulary and connectors, and Bet uses richer natural language and moderately more complex structures. The small [frequency-aware Hebrew reference](prompts/frequent-hebrew.md) is passed to every adaptation as a soft wording preference, not a whitelist or difficulty gate. Python does not classify words as too difficult and does not fail content based on level length. New adaptations receive missing terminal punctuation automatically; alphabetic separator units are repaired in code by reclassifying language-bearing units or reattaching clear Hebrew prefixes before validation. The finished Hebrew defaults to single written words, with short indivisible expressions and names kept together.
New generation flags units over four words and whole multiword sentence targets for targeted repair.
Single-word replies, a small set of conventional short replies, and short name-only units are allowed. Individual empty translations are allowed, but each story level must reach at least 75% coverage per language.

The generation workflow commits with the GitHub Actions bot, then deploys the already validated build. The generated commit does not need to trigger a second workflow.

## Security

The API key is read only by the generation job from its GitHub environment. It is never written to JSON, HTML, frontend JavaScript, or Git. `.env`, `.idea/`, `.venv/`, and generated `dist/` output are ignored.
