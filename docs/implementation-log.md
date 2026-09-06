# Implementation log

## 2026-09-06

- Removed three topic-duplicate CURRENT stories introduced by a second same-day generation run (desalination shutdowns, Mahane Yehuda renovation, and parent–teacher contact rules) and restored the issue index metadata to the cleaned 12-story issue.
- Strengthened append validation with order-independent significant-word overlap in addition to the existing source, slug, and sequence checks, so substantially rephrased versions of an existing topic are rejected during research and by repository validation.
- Fixed article rendering when generated lexical units carry leading or trailing whitespace inside clickable text. Server-rendered HTML and client-side level/translation rerenders now place boundary whitespace outside the button while preserving the unit's internal text and translations.
- Added focused generation, validation, and rendering regression tests for both observed failures.
- Added DIALOG as a minimal first-class generated story type for natural conversations useful to the learner and their family. New issues target 4 CURRENT, 3 EVERYDAY, 3 DIALOG, and 2 HISTORY entries; sourced-story counts remain flexible for a 10–13 story range.
- Reused the existing scenario metadata, diversity history, level adaptations, lexical translations, cards, and article pages for DIALOG. Added RU/EN type labels, AI-generated disclosure, source/image restrictions, dedicated prompt guidance, and focused tests without introducing a separate screenplay model or UI. Fixed new-issue counts apply only when creating a date; same-day append batches may contain any valid mix.
- Verification passed repository content validation, 34 unit tests, Python compilation, JavaScript syntax checking, the production static build, and whitespace checks. Per owner direction, no local browser run or additional independent review was performed for the DIALOG change.
- Corrected generation workflow ordering after a paid generation completed before a repository-test failure: validation and unit tests now run as a preflight before any OpenAI call, while generated content validation and the production build remain after generation.

## 2026-09-04

- Translated and recorded the supplied Russian product document in `docs/product-specification.md`; added confirmed decisions for daily UTC generation, the project Pages base path, same-day append behavior, source-linked images, interface languages, and extensible levels/locales.
- Researched the Alef/Alef Plus/Bet interpretation against Hebrew University Rothberg descriptors. Kept the requested short magazine bands and documented that Alef assumes readers can decode unpointed Hebrew.
- Prepared four complete-page visual directions and recorded the owner's choice of Direction 1, “Jerusalem Journal.”
- Added configuration-driven content contracts, validation, reading-time calculation, an OpenAI Responses API pipeline that freezes researched briefs before adaptation, search-grounded source/image-rights URLs, transactional content writes with rollback, flexible issue counts, duplicate checks, and 30-day EVERYDAY history context.
- Added the selected static frontend with home/archive/day/article routes, locale and level persistence, lexical popovers, sources, optional remote images, responsive styling, and project-Page-safe URLs.
- Added a dated sample issue with real NASA/JPL and Science Museum sources, all three initial levels, and RU/EN lexical translations.
- Added daily/manual generation and push-only deployment workflows, basic unit tests, repository setup instructions, and `.gitignore` entries for `.idea/`, virtual environments, secrets, caches, and generated output.
- Verification completed during implementation: content validation, Python compilation, JavaScript syntax check, static build, and unit tests. Final browser and review results are recorded in the handoff after the last pass.
- Applied the independent implementation review: image and rights URLs are checked against actual research results, research briefs are validated before adaptation, equivalent source URLs are deduplicated, the homepage renders the whole issue, and date/minute localization is delegated to browser internationalization for future locales.
- Final verification passed content validation, 14 unit tests, Python compilation, JavaScript syntax checking, workflow YAML parsing, the production project-path build, and link checks. Headless Firefox checks covered the desktop homepage and a narrow mobile article page; the temporary server, builds, browser profiles, screenshots, and caches were removed afterward.
- The post-fix independent confirmation review found no remaining issues or regressions.

## 2026-09-05

- Fixed the first live generation failure caused by OpenAI web-search actions returning `sources: null`; URL extraction now safely handles null or malformed search-result entries, with a regression test matching the observed response.
- Improved readability without changing the selected Jerusalem Journal direction: enlarged small interface text and controls, strengthened Hebrew headings, and increased article body size and line spacing on desktop and mobile.
- Content validation, 15 unit tests, JavaScript syntax checking, static building, and desktop/mobile headless-browser checks passed after the changes.
- Added timestamped generation diagnostics for research, adaptation, validation, retries, and transactional writes. Refactored retries so an adaptation error no longer repeats the expensive research phase.
- Prevented the observed empty-title-unit failure through the Structured Outputs schema and prompt, plus a defensive normalization that removes only zero-length units while retaining meaningful whitespace separators.
- Routed unverified search URLs into visible research-validation feedback instead of aborting before the retry loop, added a third research-only attempt, removed redundant source references only when a story retains a unique source, and strengthened the prompt against homepages, section pages, generic latest pages, and liveblogs.
- Reformatted validation diagnostics as one error per line for readable GitHub Actions logs.
- Hardened generated-URL handling by rejecting URL whitespace/control characters and escaping control characters in logs and exception reports.
- Simplified source handling by allowing source-free CURRENT/HISTORY stories and silently discarding duplicate or unverified URLs plus dependent images, so source quality alone does not trigger another paid research call.
- Made lexical rendering restore omitted spaces in both generated HTML and client-side level changes, switched all typography to system Arial, and stacked mobile story-card content so titles and metadata no longer compete for the same narrow row.
- Rebalanced generation around 4 practical CURRENT, 4 EVERYDAY, and 2 HISTORY stories; CURRENT prioritizes Israeli/local daily-life reporting, while HISTORY prioritizes local places, institutions, customs, and approaching holidays. Deprioritized technology/science spectacle and expanded conversational situations.
- Raised per-level targets to provide roughly 40–50 learner-reading minutes, required 4–5 generated paragraphs, and added localized “fully AI-generated” disclosure to EVERYDAY cards and article pages. Removed the generated 2026-09-04 issue, index entry, and matching EVERYDAY-history records for a clean retry.
- Split long adaptation output into independently validated two-story batches and enabled SDK connection retries. A dropped API connection now retries only the affected batch instead of losing one oversized all-story adaptation response.
- Made empty lexical translations non-fatal after the second adaptation attempt. The Hebrew unit is retained, untranslated units have no tooltip in the selected language, and structural validation failures remain blocking.
- Required 3–5 EVERYDAY stories in both the research prompt and research validation. Added compact summaries from the previous three calendar days to the research prompt to reduce repeated current events, history subjects, and everyday plots across issues.
- Moved the daily GitHub Actions schedule from 06:00 UTC to 01:15 UTC and updated the site footer and repository documentation.
- Kept language work in one inexpensive adaptation pass per story batch: the model is instructed to write and proofread Hebrew before segmenting and translating it. Translations may be empty for genuinely untranslatable units and must cover at least 75% per level and locale.
- Final verification passed content validation, 20 unit tests, Python compilation, JavaScript syntax checking, workflow YAML parsing, and the production static build.
