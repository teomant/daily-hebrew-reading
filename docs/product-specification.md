# Hebrew Reading Magazine — MVP Product Specification

Status: approved product requirements, translated from the Russian specification supplied by the repository owner on 2026-09-04.

This document describes a fully working MVP of a static website for daily reading in modern spoken Hebrew. The product is for learners who want to read contemporary, natural Hebrew regularly but are not yet ready for books or difficult newspaper articles.

The core idea is to give the reader a varied daily issue of interesting local/current material, relatable history, realistic everyday stories, natural dialogues, and compact practical situations. This is neither a conventional news site nor a textbook. News and history supply interesting stories and new vocabulary; generated material systematically covers language people need with family and other people around them.

The primary product principle is to select and create material according to what is interesting to read and useful for learning contemporary Hebrew, not according to what is considered the day's most important news.

## 1. Daily issue

A new issue is generated automatically every day. A typical issue contains:

- 2 real, recent stories;
- 3 purpose-written everyday stories;
- 2 purpose-written dialogues;
- 3 historical stories;
- 1 SHORTS page containing 10–11 independently generated mini-situations.

This normally produces 11 pages. Missing sourced material may make the issue smaller, but it does not expand the fixed generated allocation.

Reading time is calculated from the resulting content rather than enforced as a generation quota. CURRENT, HISTORY, and EVERYDAY articles should normally contain 4–5 developed paragraphs. DIALOG uses 8–12 short speaker turns, each on its own line. Every SHORTS item is one compact paragraph of exactly two or three complete sentences.

## 2. Content types

The five public content types are CURRENT, EVERYDAY, DIALOG, HISTORY, and SHORTS.

### CURRENT

A real, recent story from external sources. It must be understandable without extensive context, interesting on its own, suitable for a short retelling, useful for everyday vocabulary, and non-political.

CURRENT stories do not have to concern Israel. Sources may come from anywhere in the world. An issue will often contain roughly 2–4 Israel-related stories, but this is not a quota; use fewer when no strong Israeli stories are available.

### EVERYDAY

A specially generated, realistic story about ordinary adult life. It is not news. It should model situations such as shopping, transport, customer service, work, deliveries, medical visits, cafés, travel, household problems, changing plans, phone calls, and interactions with other people.

Avoid artificial classroom exchanges such as a sequence of greetings and a simple price question. Each article needs a small real-life situation with an event, action, and outcome. For example: a wardrobe delivery was promised between 10:00 and 14:00; it is nearly 14:00 and nobody has arrived; the customer calls the shop, learns what happened, and decides whether to wait another hour.

These stories should expose readers to useful constructions such as:

- עדיין לא — not yet;
- כבר — already;
- עוד מעט — soon / in a little while;
- בערך — approximately;
- לא הספקתי — I did not manage to / have time to;
- לא שמתי לב — I did not notice;
- שכחתי — I forgot;
- אמרו לי ש… — they told me that…;
- הבטיחו לי — they promised me;
- אני כבר בדרך — I am already on my way;
- אפשר להחליף? — can it be exchanged?;
- כדאי — it is worth / advisable;
- עדיף — it is preferable;
- אין לי זמן — I do not have time;
- אין לי אפשרות — I cannot / I do not have the option;
- מתי בערך? — roughly when?;
- תוך כמה זמן? — within how much time?;
- בסוף החלטתי — in the end I decided;
- נראה לי — I think / it seems to me;
- לא נורא — it is not so bad / never mind;
- אין בעיה — no problem;
- אין צורך — there is no need;
- זה לא משתלם — it is not worth it;
- מה אפשר לעשות? — what can be done?;
- נשאר — remained / is left;
- נגמר — ran out / ended;
- חסר — is missing / lacking.

### DIALOG

A specially generated short conversation for practical Hebrew learning. A new issue normally aims for about two. Dialogues normally use two speakers in familiar family and daily-life situations such as making plans, meals, shopping, school, transport, appointments, errands, neighbors, and small problems at home.

The exchange should sound like ordinary contemporary Israeli conversation, not a classroom exercise, interview, screenplay, dramatic scene, or narrated story. Use 8–12 short turns at every reading level. Planning freezes two Hebrew speaker names, and every paragraph-array item contains exactly one direct-speech turn beginning with one of those names and a colon. Adaptation receives a dialogue-specific example and focused retries; code normalizes recoverable name, colon, and alternation mistakes so an otherwise usable dialogue is not discarded for label formatting. Use natural questions, answers, clarifications, reactions, and a simple practical outcome. Do not describe the conversation in third-person prose; a mainly narrated result belongs to EVERYDAY. DIALOG uses the same scenario metadata and repetition history as EVERYDAY and has no external sources or images.

### SHORTS

One fully AI-generated page containing 10–11 independent mini-situations from ordinary life. Examples include asking who is last in a queue, how to reach a place, where to find an item, which entrance to use, or whether a seat is free. Each item is planned and adapted independently, contains one tiny interaction or action and its immediate result in exactly two or three complete sentences, and occupies one compact paragraph. The valid items are then collected into one numbered page. Each item has its own scenario metadata and repetition-history record; the page has no sources or image.

### HISTORY

A real historical story, normally three per issue. The normal sourced pool contains 12 HISTORY candidates gathered from substantially more source pages before filtering. It includes at least three stories centered on historical people, three on Israeli industry, three on culture, and two on concrete past events or ordinary-life history. The deterministic final mix prioritizes one person, one Israeli-industry, and one culture story. Present-day startups, high-tech unicorns, funding rounds, valuations, launches, and executive profiles do not qualify as Israeli-industry history.

A historical person, company, factory, institution, cultural work, event, or place is a subject, not yet a story. Discovery screens subjects compactly; after duplicate review and deterministic selection, a separate batched web-research phase must gather enough material for each selected subject to retell what actually happened: concrete actions, decisions, working methods, problems, changes, turning points, consequences, and outcomes as applicable. A shallow profile, roundup, exhibition page, anniversary program, or event listing is only a lead and must not survive selection unless further research supports a real narrative. Do not replace historical material with claims that the subject “shows,” “reflects,” or “represents” society, culture, memory, influence, or importance.

Nature sites, parks, gardens, trails, viewpoints, landmarks, fortresses, and tourist destinations are not a required family. At most two of the 12 candidates may be place-led and at most one may be archaeology-led. The first two discovery passes focus on Israeli material; broader relatable world history is reserved for a third and final fallback when sourced slots remain open.

It must be a story rather than a bare date. It does not need to relate to the publication date, current news, an anniversary, or the season. “The Edsel was introduced on 4 September 1957” is insufficient. A useful article would explain that Ford invested heavily in a new model, expected and advertised a major success, but buyers reacted very differently from the company's expectations.

HISTORY should use real sources when a trustworthy canonical URL is available. If no interesting event fits a particular date, do not force an uninteresting date connection.

## 3. Preferred CURRENT topics

Preferred topics include food; restaurants and cafés; shops and supermarkets; purchases, prices, and services; transport, cars, and city life; work and professions; technology, gadgets, applications, the internet, and AI; science and space; nature, animals, and ecology; travel and airports; museums, books, music, film, and culture; education and schools; unusual research and archaeology; consumer stories and everyday regulations; interesting human stories; and unusual business stories that are understandable through ordinary life.

Sources are not limited to Israeli media. International news, scientific, cultural, and local sources are acceptable.

## 4. Excluded topics

By default, do not use party politics, elections, politicians as principal characters, parliamentary or coalition disputes, ideological arguments, war, combat, military operations, terrorism, geopolitical or diplomatic conflicts, serious crime reporting, murder, mass tragedies, outrage bait, clickbait, or stories that require extensive political context.

Practical decisions by a government, city, school, or institution are acceptable when the story itself is non-political. New school rules for phone use are suitable; a political dispute about those rules is not.

## 5. Selecting real stories

News importance is not the main criterion. The primary internal criterion is Language Value, assessed through four dimensions:

1. **Vocabulary usefulness** — frequent verbs, everyday nouns, useful adjectives, conversational expressions, and constructions encountered in real life. This is the most important dimension.
2. **Explainability** — whether an Alef learner can understand the story without extensive background.
3. **Interest** — whether the story has a simple, engaging central idea.
4. **Freshness** — how recent it is.

Freshness matters less than language value. Stories from today, yesterday, or the previous several days are acceptable. A good two-day-old story is preferable to a boring story from today.

## 6. One article, one idea

Each story must have one clear central subject. Do not overload a short article with context.

For a new application feature, explain what appeared, what it does, how a person can use it, and why it is interesting; do not recount the company's entire history. For a restaurant closure, explain how long it operated, why people knew it, what happened, and how regular customers reacted; do not turn it into a history of the country's restaurant industry.

## 7. Article formats and levels

The initial reading bands align approximately with Alef (`A1.1`), Alef Plus (`A1.2`), and Bet (`A2`). These are editorial adaptation targets, not a placement test or formal certification. The distinction is vocabulary, grammar, sentence shape, and natural expression—not a requirement for harder levels to contain more words.

Reading levels are configuration-driven, ordered definitions with stable IDs, display labels, approximate proficiency mapping, adaptation instructions, and reading-speed assumptions. Rendering, generation, validation, and navigation must iterate the configured levels rather than hardcode exactly three.

### Alef — א

Use very common concrete words, familiar verb forms, active clauses, and one event or thought per short sentence. Avoid formal connectors, abstract nominal language, dense construct chains, and nested clauses. The result is simple adult Hebrew, not children's prose.

### Alef Plus — א+

Use a broader but still common everyday vocabulary than Alef, more past and future forms, simple cause and effect, natural connectors, fixed expressions, and occasional short subordinate clauses.

### Bet — ב

Use a wider everyday vocabulary, more precise verbs and adjectives, natural connectors, comparisons, reactions, common colloquial constructions, and moderately more complex sentences without becoming dense newspaper prose.

## 8. Do not pad articles

Length follows the content format: full articles use developed paragraphs, dialogues use 8–12 turns, and SHORTS items use one compact paragraph. Do not use length to distinguish Alef, Alef Plus, and Bet. Python must not reject an adaptation because it considers a word too difficult or because one level is not longer than another. Do not pad through repetition, empty introductions, invented details, or artificially complex phrasing.

## 9. Hebrew style

Use modern spoken Israeli Hebrew: language in which a contemporary Israeli might naturally tell or explain something to another person.

Avoid biblical or religious language, elevated literary prose, bureaucracy, dense newspaper style, and needlessly formal constructions. For example, prefer אחרי מה שקרה, העירייה הודיעה שהיא עוצרת את הפרויקט בינתיים over בעקבות ההתפתחויות הודיעה העירייה על השהיית הפרויקט. At Alef, simplify further to העירייה החליטה לעצור את הפרויקט עכשיו.

The MVP does not need niqqud. Consequently, even the Alef band assumes the reader has moved beyond initial alphabet and decoding instruction.

## 10. All configured levels tell the same story

Do not generate level adaptations independently in ways that introduce different facts. The initial Alef, Alef Plus, and Bet versions—and any future configured versions—must share one frozen factual contract. Every HISTORY level preserves the principal actions, consequential change or turning point, and outcome; simpler levels may compress secondary dates, names, qualifiers, and context, but must not replace the story with generalities. If an article still violates its output or factual-coverage validation after one focused retry, omit that article and continue adapting the others rather than failing the issue.

For CURRENT, the pipeline is: sources → factual brief → level adaptation with lexical units and contextual translations. For HISTORY, it is: compact sourced screening brief → duplicate review and selection → selected-only batched deep research → 8–12 ordered factual story beats → retold level adaptation with lexical units and contextual translations. For EVERYDAY and DIALOG, it is: scenario brief → level adaptation with lexical units and contextual translations. Within adaptation, Hebrew prose is written and proofread before it is segmented.

Alef may omit details and Bet may expand them, but central facts and events must remain consistent.

## 11. Generated-scenario diversity history

Generated everyday stories, dialogues, and individual SHORTS items must not repeat too frequently. Keep their scenario history in Git. For recent entries, retain the date, domain, scenario, main lexical themes, and target vocabulary. Consider approximately the previous 30 days when generating a new issue.

For a new complete issue, the generated allocation is exactly three EVERYDAY stories, two DIALOG stories, and one SHORTS page targeting nine items and requiring at least eight. The normal sourced target is two CURRENT and three HISTORY stories. Discovery returns six CURRENT and 12 HISTORY screening candidates before filtering. Duplicate-reviewed but unselected HISTORY candidates remain in a reserve queue, with Israel-focused passes ordered ahead of the worldwide fallback. Deep research normally uses one batched call for the selected three. Two consecutive HISTORY research request failures abort generation rather than silently publishing an all-generated substitute issue. Missing sourced slots do not expand the generated allocation.

A same-day append generates only fully AI-generated EVERYDAY or DIALOG stories, in any mix. It does not generate CURRENT or HISTORY entries and does not enable web research. The output schema and pre-adaptation validation both enforce this restriction.

## 12. Generated-scenario domains

Example domains include shopping and payments; food and cooking; transport and navigation; services and appointments; work; home and family; neighbors and community; learning and classes; sports and exercise; pets and animals; clothing and personal care; hosting and celebrations; arts and events; day trips and travel; volunteering; household money and subscriptions; parenting and school; nature and outdoor life; health and wellbeing; and digital administration. This list is extensible.

## 13. Do not repeat scenarios

Domain and scenario are different. The restaurant domain can recur later, but articles should not repeat nearly identical plots. Different restaurant scenarios include an unavailable dish, arriving without a reservation, waiting too long, receiving the wrong dish, splitting the bill, changing a reservation, or recovering an item left behind.

As a soft guideline, avoid using the same principal domain several times in one week and avoid repeating the same scenario for several weeks. The purpose is to prevent the feeling that only the names changed in a recently read story.

## 14. Vocabulary may repeat

Frequent vocabulary does not need to be new every day; repetition is useful. Words such as להגיע, לחכות, לבחור, כדאי, לבדוק, להזמין, להשתמש, and לשלם may recur. Avoid repeating plots, not language.

## 15. Generated-scenario vocabulary planning

EVERYDAY stories should gradually cover varied conversational vocabulary. One day may emphasize waiting, changing plans, requests, and replacement; another may emphasize comparison, payment, clarification, and mistakes. Do not build a complex curriculum system. Recent scenarios and lexical themes are enough.

## 16. Lexical units

The principal interactive feature is translation of words and expressions. Hebrew text must be segmented into useful lexical units, not merely split on spaces. A unit can be a single word, a fixed expression, a multi-word construction, or a proper noun.

For example, מזג אוויר is one unit translated as “погода” in Russian and “weather” in English; שם לב is one unit translated as “обратить внимание” and “notice / pay attention”; בסופו של דבר is one unit translated as “в итоге / в конце концов” and “in the end / eventually.” Do not mechanically split fixed expressions when doing so makes comprehension worse.

## 17. Translation coverage

Almost all main Hebrew text must be interactive so a reader can select nearly any unfamiliar word or expression. For each meaningful lexical unit, store the Hebrew text, a translation map keyed by stable locale code, and its type. The initial translation locales are `ru` and `en`, but content rendering and validation must use each issue's configured translation locales rather than fixed Russian and English fields. The model should attempt every meaningful unit and translate it according to its meaning and grammatical role in the complete sentence, not as an isolated dictionary entry. An individual translation may be empty when no useful direct translation exists, but each story level must have at least 75% coverage in every configured translation language.

The MVP needs these types: `word`, `expression`, `properNoun`, and `separator`. Most meaningful units contain one to three Hebrew words; four words are reserved for indivisible fixed expressions, proper names, or phrases whose meaning would be damaged by splitting. A complete sentence or independent clause must not be stored as one lexical unit. Attached Hebrew prefixes remain part of their written word. Ordinary single spaces between meaningful units may be omitted from JSON and reconstructed by the renderer; separators are reserved for punctuation or whitespace whose exact placement matters and need no translation.

The MVP does not need roots, binyanim, conjugation, transliteration, niqqud, word frequency, or grammatical analysis.

## 18. Translation tooltip or popover

On desktop, hover reveals a translation and keyboard focus must provide the same access. On mobile, tapping reveals it and tapping outside closes it. The reader chooses one available translation language and sees only that language. The initial choices are RU and EN. The popover must not move the text or break the layout.

The site interface itself also has an independent language selector, initially with Russian and English options. Interface language changes navigation, labels, categories, dates, reading-time text, source labels, and accessibility text; it does not translate the Hebrew article content. Interface strings live in locale dictionaries keyed by locale code, and UI components must not contain language-specific branching. Persist the selected interface language in `localStorage`.

## 19. Site structure and URLs

The site is fully static. Navigation follows Home → Day → Article. Example paths are `/`, `/2026-09-04/`, and `/2026-09-04/sheep-save-glaciers/`. Every article has its own page.

## 20. Home page

The home page shows the latest available issue, its date, story count, approximate reading time, story list, access to earlier days or the archive, and a localized button that selects a random article from any available issue. It must not advertise a fixed 40–50-minute duration or claim a publication time. It is not a large marketing landing page; its purpose is to let the reader start quickly.

## 21. Day page

The page for a date is that issue's table of contents. It shows the date, story count, approximate total reading time, and article cards. Each card contains the Hebrew title, category, short teaser, and approximate reading time, and links to the article page.

## 22. Article page

An article page contains a link back to the issue, date, category and content type, title, reading time, level selector (`א`, `א+`, `ב`), translation-language selector (`RU`, `EN`), interface-language selector (`RU`, `EN`), text with lexical popovers, available sources for CURRENT and HISTORY, and previous/random/next article navigation. The random control selects from every available issue while excluding the article currently open.

Persist the selected level, translation language, and interface language between pages using `localStorage` for the MVP. Translation language and interface language are separate preferences.

## 23. Reading time

Show approximate reading time for each article and issue. A simple calculation based on Hebrew word count and level is sufficient. It should reflect that a learner reads more slowly than a native speaker, without imposing a fixed issue-duration target.

## 24. Sources and external images

CURRENT and HISTORY stories may store real publisher, title, and URL data when trustworthy canonical links are available. Missing, duplicate, malformed, or unverified links are discarded. An empty source list is valid for HISTORY and does not invalidate an otherwise usable researched fact pack; source metadata is helpful reader attribution, not a publication gate. CURRENT discovery should still return a real source because it represents a recent external event. EVERYDAY and DIALOG have no sources. Never create fictional links or present generated scenarios as news. The content type must be explicit in stored data.

A CURRENT or HISTORY story may also have one optional image linked directly from one of its original source articles. Store the HTTPS image URL, the source article URL, publisher or credit, localized alt text, and an HTTPS usage-rights/policy URL with a short factual label. The generator may return an image only when the image, source, and policy URLs all appear in its actual web-research results; otherwise it returns no image. The card and article page may display it with source attribution and links to the original article and usage policy. Do not download or commit third-party images for the MVP. If the URL is missing, rejected, or later stops loading, render the story normally without an image or broken layout. Images are optional and must only be used when the applicable source and usage rights allow embedding; generation must not invent ownership or licensing information. EVERYDAY and DIALOG do not use sourced images.

## 25. Content storage

The MVP does not need a database. Store content in Git, using one primary JSON file per day plus an issue index and everyday-history file, for example:

```text
content/
  index.json
  everyday-history.json
  2026-09-04.json
  2026-09-05.json
config/
  site.json
  reading-levels.json
i18n/
  en.json
  ru.json
```

A daily JSON file contains its date, available reading-level IDs, available translation-locale codes, and ordered pages. Ordinary stories contain their type, category, English internal brief, sources, optional image, configured level variants, teaser, title, paragraphs, and lexical annotations. EVERYDAY and DIALOG store scenario metadata. A SHORTS page stores 10–11 ordered `shortItems` metadata records and one corresponding paragraph per item at every level. Newly researched HISTORY stories retain 8–12 ordered English `storyBeats` as their factual contract. `index.json` lists available dates, while `everyday-history.json` tracks full generated stories and each SHORTS item independently.

## 26. Illustrative story shape

The precise schema may differ, but it must retain the meaning of the following structure:

```json
{
  "id": "late-furniture-delivery",
  "slug": "late-furniture-delivery",
  "type": "everyday",
  "category": "everyday",
  "everydayMeta": {
    "domain": "delivery",
    "scenario": "late_delivery",
    "targetVocabulary": ["לחכות", "להגיע", "עדיין", "בערך"]
  },
  "sources": [],
  "levels": {
    "alef": {"teaser": "...", "title": [], "paragraphs": []},
    "alefPlus": {"teaser": "...", "title": [], "paragraphs": []},
    "bet": {"teaser": "...", "title": [], "paragraphs": []}
  }
}
```

CURRENT and HISTORY use real sources rather than scenario metadata. DIALOG reuses `everydayMeta` and adds two planned Hebrew `dialogSpeakers`. A SHORTS page stores ordered `shortItems` metadata so each mini-situation remains independently traceable in scenario history.

## 27. CURRENT generation

Inspect substantially more candidates than the two final CURRENT slots, filter out duplicates, politics, and unsuitable topics, and evaluate practical spoken-language value. Reject remote disasters, rescue missions, specialist science, and technology stories without direct relevance to ordinary life. Do not select a collection of top headlines by default.

## 28. EVERYDAY generation

Read the recent scenario-history data, remove overly similar ideas, select three EVERYDAY situations, create scenario briefs, and adapt them into the configured levels. Planning uses canonical broad domains and keeps the five full generated stories on distinct domains within the issue. Vary interaction shapes as well as settings and include positive cooperative activities. Mark every generated story visibly as fully AI-generated.

## 29. DIALOG generation

Generate two short dialogues for each new issue. Planning supplies exactly two binding Hebrew speaker names. Store every turn as its own paragraph-array item so it appears on a separate line. The prompt includes a compact literal example; generated dialogue adaptation receives three focused attempts. Before validation, code rewrites recoverable leading labels into the planned alternating `name:` form. A remaining style imperfection is logged but does not remove an otherwise schema-valid dialogue.

## 29a. SHORTS generation

Plan eleven independent short situations and adapt each in its own request with exactly one paragraph per level. Each brief supports exactly two or three complete sentences covering one tiny practical action or question and its immediate answer or result. Keep at least ten valid items, assemble at most eleven in their planning order, and publish them as one numbered SHORTS page. Record every item—not merely the containing page—in generated-scenario history.

## 30. HISTORY generation

Return 12 distinct compact HISTORY screening candidates from a substantially larger search and normally select three. The first two passes require model-reported lane minimums of six Wikimedia/reference candidates, three National Library or Historical Jewish Press candidates, two state visual-archive candidates, and one Israeli culture-archive candidate. Require at least three person, three Israeli-industry, three culture, and two event candidates. The selected three contain one person, one Israeli-industry story, and one culture story. Retain reviewed reserves and deeply research only selected subjects. Each sufficient pack still has 8–12 ordered factual beats; reduced total research must not weaken evidence for an individual published HISTORY article.

## 31. Facts and generation

Language adaptation must not freely invent details for real stories. A factual brief must precede all CURRENT versions; a compact brief and ordered factual beats must precede new HISTORY versions. HISTORY adaptation retells those beats rather than describing the source or offering generic commentary about the subject. Every level of a newly researched HISTORY story must report coverage of all required beat IDs; missing coverage retries the adaptation and then prevents that article from being published without blocking the rest of the issue. Word count remains non-blocking. Never hallucinate details, repeat facts, or add filler to meet a length target.

## 32. OpenAI API

Use the OpenAI API for sourced discovery and selection, sourced semantic duplicate review, selected-HISTORY research, generated-scenario planning, level adaptation, lexical segmentation, and Russian and English translations. A normal issue first makes up to three web-enabled discovery requests of 18 compact candidates. A separate no-web request plans the three EVERYDAY and two DIALOG stories, and another plans the eleven SHORTS items. Each full generated story and each SHORTS item is adapted independently.

Use `gpt-6-luna` for every discovery, research, planning, adaptation, annotation, and translation request, with low reasoning effort. Supply the key through `OPENAI_API_KEY`; a local `OPENAI_MODEL` override may be used for tests or explicit experiments. Store the key only in a GitHub Actions secret or runtime environment. It must never enter Git, frontend assets, JSON content, HTML output, logs, or error messages.

In the target repository, `OPENAI_API_KEY` is configured as a secret in the GitHub Actions environment named `daily-hebrew-reading`. The issue-generation job explicitly declares that environment and pins `OPENAI_MODEL` to `gpt-6-luna` in the workflow.

## 33. Prompts

Keep editorial rules separate from application code. Maintain six instruction groups:

- **Editorial:** CURRENT research, Language Value, political exclusions, interest, and HISTORY selection.
- **Deduplication:** binding semantic comparison of sourced candidates with prior-day and current-run sourced briefs.
- **Selected HISTORY research:** source-backed narrative beats for only the selected subjects and any reserve replacements.
- **Everyday:** realistic situations, diversity, recent topics, and useful conversational vocabulary.
- **Dialog:** short, natural family and daily-life conversations.
- **Shorts:** compact independent ordinary-life situations collected on one page.
- **Adaptation:** Alef, Alef Plus, Bet wording progression, modern spoken Hebrew, lexical units, RU/EN translation, no filler, and a separate DIALOG-only literal structure example.

## 34. Automation

A GitHub Actions workflow is configured to run daily at 01:37 UTC. Its first job logs the event name, event schedule expression, runner UTC time, run identity, actors, ref, head SHA, workflow ref/SHA, resolved target date, requested append count, and issue-existence decision. This diagnostic job must not receive OpenAI credentials. If the resolved issue already exists and no positive append was explicitly requested, the remaining jobs are skipped before Python setup, dependency installation, tests, secrets, or AI calls. When generation is needed, it validates the checked-out content and runs the unit tests before calling OpenAI so repository failures do not consume generation spend. It then generates a complete issue or explicit append, validates the changed content, updates generated-scenario history, writes the JSON, commits and pushes the content, builds the site, and deploys GitHub Pages. It must also support manual execution through `workflow_dispatch`, exposed in the repository's Actions tab as a **Run workflow** button.

The manual run accepts an optional target date, resolved as the current UTC date when omitted, and a requested number of additional stories from 0–10, defaulting to 0. When no issue exists for the target date, generation creates the normal complete issue regardless of the append input. When an issue already exists, zero is a no-op and a positive explicit value preserves every existing story and appends that many new stories instead of replacing the file. Append batches contain only EVERYDAY or DIALOG stories in any mix; the fixed new-issue counts do not apply. It recalculates issue metadata and navigation, updates generated-scenario history, validates the combined issue, and only then commits it.

Generation separates sourced discovery, sourced duplicate review, selected-HISTORY research, full generated planning, SHORTS planning, and adaptation. Adaptation receives frozen briefs plus the level, segmentation, and translation contracts. Level difficulty is prompt-driven: Alef uses frequent concrete wording and simple clauses, Alef Plus broadens ordinary vocabulary and connectors, and Bet uses richer natural language and moderately more complex structures. Python does not score word difficulty or enforce increasing length. After adaptation, generation removes empty units, repairs alphabetic separators, normalizes DIALOG labels, and restores missing terminal punctuation before validation. Clear one-letter Hebrew prefixes are reattached to the next word; other language-bearing separators are reclassified as meaningful units. DIALOG formatting and style receive focused retries but do not silently remove an otherwise public-schema-valid dialogue.

Each planning stage receives only its relevant compact forbidden records from the existing issue and recent issues. Sourced discovery defines a CURRENT duplicate as the same central subject and underlying event, action, announcement, change, project, or outcome; equivalent URLs, alternate coverage, cosmetic rewrites, later status reports, continuing consequences, changed statistics, and minor follow-ups remain duplicates. For HISTORY, reuse of the same named primary subject—such as a street, building, archaeological site, institution, person, event, object, or custom—is a duplicate even when another source, period, excavation, archaeological layer, fact, or angle is used. Generated planning defines a duplicate by the practical problem or goal, interaction, and resolution; an identical recent scenario ID is always a duplicate, while sharing only a domain or vocabulary is allowed. Forbidden records are comparison data, never search suggestions or templates.

For the normal five sourced slots, each discovery attempt returns exactly 18 compact candidates: six CURRENT and 12 HISTORY. The first two passes search across Israel and allocate HISTORY leads across the documented lanes; the third pass is a worldwide fallback for still-open sourced slots. The HISTORY pool contains at least three `person`, three `israeliIndustry`, three `culture`, and two `event` records; `place` is capped at two and `archaeology` at one. Deterministic selection chooses one person, one Israeli-industry, and one culture story for the three HISTORY slots. Candidate-level failures remove only affected candidates; pool-mix findings become retry guidance.

The separate LLM reviewer must classify every surviving candidate exactly once from its compact brief and URLs, comparing underlying events and named historical subjects rather than wording. Its duplicate verdicts are binding and removed candidates are never selected, reserved, adapted, or published. Missing, malformed, or failed review coverage fails closed by discarding the unreviewed batch, but does not fail publication. The second discovery pass remains Israel-focused and must search new leads rather than alternate coverage, translations, updates, or renamed versions of rejected stories. Only the third and final pass becomes a worldwide replacement search. All editorial, safety, source, and novelty rules remain active. A remaining sourced shortfall reduces issue size rather than expanding the generated allocation.

After selection, one batched web request researches the three chosen HISTORY subjects. Every sufficient pack still contains 8–12 unique factual beats covering setup, action, turning point, and outcome. Generated planning creates exactly three EVERYDAY and two DIALOG briefs for a normal fresh issue. SHORTS planning separately creates eleven mini-situation briefs; each is adapted independently and 10–11 valid items are collected on one page.

Retries are fresh Responses API requests containing compact retained records and exact validation feedback. They do not use `previous_response_id`, because inherited input remains billable and stale rejected output can anchor the correction. Before every OpenAI request, generation logs the complete phase-specific system and user prompt with role and phase markers. Python also rejects duplicate or near-duplicate slugs, briefs, canonicalized source URLs—including normal and `/amp` forms of the same article—and exact generated scenario IDs before adaptation. Generation runs are serialized so simultaneous scheduled or manual invocations cannot race and overwrite one another. A failed append leaves the existing issue unchanged.

The repository's default branch is `master`. An ordinary push to `master` does not generate an issue; it only validates, builds, and deploys the existing content. Generation commits also target `master`.

## 35. GitHub Pages

The target repository is `https://github.com/teomant/daily-hebrew-reading`, and the target project-site URL is `https://teomant.github.io/daily-hebrew-reading/`. Asset paths, content paths, links, and article URLs must all respect the `/daily-hebrew-reading/` base path.

## 36. Technology constraints

Keep the MVP simple. Prefer Python, HTML, CSS, vanilla JavaScript, JSON, GitHub Actions, and GitHub Pages. Do not add a database, backend, authentication, Docker, Kubernetes, Next.js, React, external hosting, or a CMS without a demonstrated need and explicit approval. The delivered site is entirely static.

## 37. Reliability

Before publishing generated content, validate at least:

- valid JSON;
- an ID and slug for every story;
- every level declared by the issue;
- non-empty text;
- at least 75% contextual translation coverage per story level and configured translation language;
- valid source metadata when a story has sources;
- domain and scenario for EVERYDAY and DIALOG;
- no duplicate slugs or duplicate source stories;
- optional image metadata uses safe HTTPS URLs, refers to one of the story's source articles, includes an independently researched usage-rights/policy URL and factual rights label, and contains attribution plus alt text for the issue's translation locales.

If generation fails, do not publish a partial issue or damage earlier content. The existing site must remain available and the workflow must fail visibly.

## 38. Sample content

Include sample issue content so the frontend can be tested without an OpenAI API key. Existing archived samples remain valid without SHORTS or DIALOG backfilling; newly generated issues use the five-type mix. Do not present invented current news as factual reporting.

## 39. User experience

The product should feel like a small daily magazine for a full commute. A day page shows the date, story count, approximate reading time, a level selector, and concise cards for locally relevant CURRENT, practical EVERYDAY, natural DIALOG, and relatable HISTORY entries. Opening one should provide a calm reading experience followed by a simple move to the next.

## 40. Product philosophy

The experience is a daily collection of short, interesting stories, real-life situations, and ordinary conversations through which the reader gradually understands more normal contemporary Hebrew. Language value wins over news importance; natural contemporary Hebrew wins over newspaper style; repetitive generated situations are replaced; and a text that would require filler is shortened.

## 41. Required MVP delivery

Deliver a complete MVP containing daily generation and safe same-day appends; CURRENT research and selection; HISTORY research; EVERYDAY, DIALOG, and grouped SHORTS generation with repetition protection; the three initial configurable Hebrew levels; extensible interface and translation locales; lexical annotation; Russian and English translations; Git-based content storage; validation; optional externally linked source images; static-site building; home, archive/day, and separate article pages; level and locale switches; hover/tap translations; sources; previous/next navigation; GitHub Actions; GitHub Pages deployment; sample content; basic tests; and a README.

After implementation, run tests, validate content, build the static site, inspect the principal pages, and fix discovered defects. The handoff report must state what was implemented, major decisions, successful checks, and manual GitHub configuration required from the repository owner.

## 42. Visual design approval gate

Before frontend implementation begins, prepare 3–4 distinct visual directions for owner review. Each direction must demonstrate the complete page family—home, archive, day, and article—as well as representative desktop and mobile states and the translation popover. The owner chooses a direction and may request adjustments; frontend work begins only after that approval.

The owner selected Direction 1, **Jerusalem Journal**, on 4 September 2026. The production frontend should carry forward its restrained editorial typography, warm paper background, deep teal structure, coral accent, fine rules, square controls, calm reading width, and source-image treatment. The prototype is a visual reference rather than production markup.
