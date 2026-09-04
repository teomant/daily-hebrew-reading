# עברית היום — Daily Hebrew Reading

A static daily magazine for learners reading modern spoken Israeli Hebrew. Each issue combines sourced CURRENT stories, realistic EVERYDAY situations, and a sourced HISTORY story at configurable reading levels. Almost all Hebrew text is selectable for Russian or English translation.

The repository contains a complete sample issue, so the site can be built and tested without an OpenAI key. The production URL is expected to be `https://teomant.github.io/daily-hebrew-reading/`.

## What is included

- Static home, archive, day, and article pages in the selected “Jerusalem Journal” design.
- Configurable reading levels (`א`, `א+`, `ב` initially) and interface/translation locale registries (`ru`, `en` initially).
- Persisted reading level, translation language, and interface language preferences.
- Keyboard, hover, and tap translation popovers.
- Source links and optional externally hosted, attributed source images with graceful failure.
- Two-phase OpenAI Responses API generation: web research freezes briefs/source metadata, then a separate strict-output adaptation creates the configured levels.
- Safe same-day append behavior; existing stories are preserved and duplicates are rejected.
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
export OPENAI_MODEL="gpt-5.4-mini"
python -m src.generate_issue --date 2026-09-04
```

If that date does not exist, the generator creates a normal full issue. If it already exists, it appends three stories by default:

```bash
python -m src.generate_issue --date 2026-09-04 --additional-stories 2
```

Generation validates a complete candidate before replacing any repository content. A failed call or invalid batch exits with an error and leaves the published site unchanged.

## Content and configuration

- `content/YYYY-MM-DD.json` — complete ordered issue.
- `content/index.json` — dates, story counts, and estimated reading times.
- `content/everyday-history.json` — scenario history used to reduce repetition.
- `config/site.json` — base path, enabled locales, defaults, flexible new-issue count range, and the three-day previous-issue context window.
- `config/reading-levels.json` — ordered level IDs, labels, word guidance, and reading speeds.
- `i18n/*.json` — interface dictionaries. Adding a locale requires a matching dictionary and adding its code to `site.json`.
- `prompts/*.md` — editorial, everyday-scenario, and adaptation rules.

Old issues list their own available levels/locales and remain readable when new ones are configured later. The validator rejects missing adaptations or translations within an issue.

## GitHub setup

The repository owner needs to configure these once:

1. In **Settings → Pages**, keep **Source: GitHub Actions**. No custom or verified domain is required for the free `github.io` address.
2. In **Settings → Environments**, use the environment named `daily-hebrew-reading`.
3. In that environment, add secret `OPENAI_API_KEY` and non-secret variable `OPENAI_MODEL` (currently `gpt-5.4-mini`). The existing screenshot configuration matches this contract.
4. Under **Settings → Actions → General → Workflow permissions**, allow **Read and write permissions** so the generator can commit `content/` to `master`.

The OpenAI API is billed separately from ChatGPT Plus. The API uses the credits on the API account; GitHub Pages is free for a public repository under GitHub's normal Pages/Actions quotas.

## Running the workflows

- **Generate daily issue** runs at `06:00 UTC` and can also be started from **Actions → Generate daily issue → Run workflow**.
- Leave `date` blank to use the current UTC date. Enter an existing date to append rather than replace. `additional_stories` controls the append size; it is ignored for a new full issue.
- **Validate and deploy site** runs on an ordinary push to `master` and never calls OpenAI.

Generation logs timestamp each research, adaptation, validation, and write phase, including elapsed API-call time and one validation error per line. Research has up to three attempts for invalid story data. Missing sources are allowed; duplicate or unverified source URLs and their dependent images are discarded without retrying research. Adaptation runs in two-story batches so long issues do not depend on one oversized API response; a failed request retries only its batch, and the factual briefs are not researched again.

Empty lexical translations are retried once during adaptation. If the second attempt still contains only translation gaps, the batch is accepted: Hebrew remains visible and untranslated units are rendered without an interactive tooltip. Structural content errors still fail the workflow.

The generation workflow commits with the GitHub Actions bot, then deploys the already validated build. The generated commit does not need to trigger a second workflow.

## Security

The API key is read only by the generation job from its GitHub environment. It is never written to JSON, HTML, frontend JavaScript, or Git. `.env`, `.idea/`, `.venv/`, and generated `dist/` output are ignored.
