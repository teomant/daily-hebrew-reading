# Hebrew Reading Magazine — MVP Product Specification

Status: approved product requirements, translated from the Russian specification supplied by the repository owner on 2026-09-04.

This document describes a fully working MVP of a static website for daily reading in modern spoken Hebrew. The product is for learners who want to read contemporary, natural Hebrew regularly but are not yet ready for books or difficult newspaper articles.

The core idea is to give the reader a daily issue containing roughly 40–50 minutes of interesting local/current material, relatable history, realistic everyday stories, and natural dialogues. This is neither a conventional news site nor a textbook. News and history supply interesting stories and new vocabulary; everyday texts and dialogues systematically cover language people need with family and other people around them.

The primary product principle is to select and create material according to what is interesting to read and useful for learning contemporary Hebrew, not according to what is considered the day's most important news.

## 1. Daily issue

A new issue is generated automatically every day. A typical issue contains:

- 3–5 real, recent stories, normally 4;
- 2 purpose-written everyday stories;
- 2 purpose-written dialogues;
- 7 historical stories.

This normally produces 15 stories and may range from 13–16 as the number of sourced stories varies. Treat two EVERYDAY and two DIALOG entries as editorial targets; never fill the flexible CURRENT or HISTORY allowance with weak material.

The target reading time is approximately 40–50 learner minutes, enough for a typical commute. CURRENT, HISTORY, and EVERYDAY articles should normally contain 4–5 developed paragraphs rather than collapsing a story into three sentences. DIALOG instead uses 8–12 short speaker turns, each on its own line.

## 2. Content types

The four content types are CURRENT, EVERYDAY, DIALOG, and HISTORY.

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

The exchange should sound like ordinary contemporary Israeli conversation, not a classroom exercise, interview, screenplay, dramatic scene, or narrated story. Use 8–12 short turns at every reading level. Every paragraph-array item contains exactly one direct-speech turn, starts with a consistent Hebrew speaker name and colon, and is displayed as its own line. Never put two speakers in one paragraph item. Use natural questions, answers, clarifications, reactions, and a simple practical outcome. Do not describe the conversation in third-person prose; a mainly narrated result belongs to EVERYDAY. Avoid long speeches, artificial repetition, exaggerated slang, and vocabulary included only to demonstrate a rule. DIALOG uses the same scenario metadata and repetition history as EVERYDAY and has no external sources or images.

### HISTORY

A real historical story, normally seven per issue. The normal sourced pool contains 24 HISTORY candidates gathered from substantially more source pages before filtering. It must include at least six stories centered on historical people, six on Israeli industry, companies, manufacturers, brands, cooperatives, factories, trades, products, or industrial development, six on culture, and four on concrete past events or ordinary-life history. Culture includes literature, music, theater, cinema, visual art, dance, design, architecture, food culture, publishing, and broadcasting. Present-day startups, high-tech unicorns, funding rounds, valuations, launches, and executive profiles do not qualify as Israeli-industry history. Museums qualify only when the story centers on cultural creation, collections, or influence rather than a building to visit.

A historical person, company, factory, institution, cultural work, event, or place is a subject, not yet a story. Discovery screens subjects compactly; after duplicate review and deterministic selection, a separate batched web-research phase must gather enough sourced material for each selected subject to retell what actually happened: concrete actions, decisions, working methods, problems, changes, turning points, consequences, and outcomes as applicable. A shallow profile, roundup, exhibition page, anniversary program, or event listing is only a lead and must not survive selection unless independent research supports a real narrative. Do not replace historical material with claims that the subject “shows,” “reflects,” or “represents” society, culture, memory, influence, or importance.

Nature sites, parks, gardens, trails, viewpoints, landmarks, fortresses, and tourist destinations are not a required family. At most two of the 24 candidates may be place-led, and each needs an exceptional, specific human story rather than a generic preservation, visitor, or “nature and history meet” hook. At most one candidate may be led by archaeology. The first seven HISTORY candidates—and the deterministic Python selection of the seven published slots—contain at least two person stories, two Israeli-industry stories, two culture stories, and one event or exceptional place story; they contain no archaeology and at most one place. Broader relatable world history remains acceptable on a retry, while missing Israeli-industry coverage must still be supplied.

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

## 7. Article lengths and levels

The initial reading bands align approximately with the Rothberg International School scale: Alef at the end of beginner Alef (`A1.1`), Alef Plus as advanced Alef (`A1.2`), and Bet (`A2`). These are editorial adaptation targets, not a placement test or formal certification. Rothberg's reading descriptors use approximately 100 words for A1.1, 200 for A1.2, and 300 for A2, so the shorter magazine ranges below are intentionally conservative. See the [Rothberg language-level self-assessment](https://overseas.huji.ac.il/wp-content/uploads/2019/07/ENGLISH-EVAL.pdf), [Alef syllabus](https://overseas.huji.ac.il/wp-content/uploads/2019/08/Syllabus-for-Level-Aleph.pdf), and [Bet syllabus](https://overseas.huji.ac.il/wp-content/uploads/2023/01/Syllabus-Level-Bet-2022.pdf).

Reading levels are configuration-driven, ordered definitions with stable IDs, display labels, approximate proficiency mapping, length guidance, adaptation instructions, and reading-speed assumptions. Rendering, generation, validation, and navigation must iterate the configured levels rather than hardcode exactly three. Newly generated issues record their available level IDs; adding a future level does not require backfilling old issues before they remain readable.

### Alef — א

Approximately 155–205 words, targeting about 180. This targets a learner near the end of beginner Alef/A1.1 who can already decode Hebrew text, not an absolute beginner learning the alphabet. Use four short paragraphs, short sentences, simple structure, frequent vocabulary, few complex subordinate clauses, and a clear sequence of events. The result is simple adult Hebrew, not children's prose.

### Alef Plus — א+

Approximately 190–250 words, targeting about 220, corresponding approximately to advanced Alef/A1.2. Use 4–5 paragraphs. It may use more past tense, cause and effect, natural connectors, simple subordinate clauses, more fixed expressions, and somewhat richer vocabulary.

### Bet — ב

Approximately 235–305 words, targeting about 270, corresponding approximately to Bet/A2. Use 4–5 developed paragraphs. This is reasonably natural contemporary Hebrew and may include more detail, causes, comparisons, reactions, and conversational constructions, including common colloquial expressions, without becoming dense newspaper prose.

## 8. Do not pad articles

Word counts are editorial targets rather than publication gates for CURRENT, EVERYDAY, DIALOG, and archived HISTORY. Before segmentation, adaptation should estimate the Hebrew body word count and make one supported revision toward the configured target when a version is below its suggested minimum. Do not lengthen an article through repetition, empty introductions, generic conclusions, unnecessary adjectives, invented details, or artificially complex phrasing. Newly researched HISTORY is the deliberate exception: its source pack must be rich enough for every level to reach configured `minimumWords`, and falling below that minimum blocks publication after the normal adaptation retry.

## 9. Hebrew style

Use modern spoken Israeli Hebrew: language in which a contemporary Israeli might naturally tell or explain something to another person.

Avoid biblical or religious language, elevated literary prose, bureaucracy, dense newspaper style, and needlessly formal constructions. For example, prefer אחרי מה שקרה, העירייה הודיעה שהיא עוצרת את הפרויקט בינתיים over בעקבות ההתפתחויות הודיעה העירייה על השהיית הפרויקט. At Alef, simplify further to העירייה החליטה לעצור את הפרויקט עכשיו.

The MVP does not need niqqud. Consequently, even the Alef band assumes the reader has moved beyond initial alphabet and decoding instruction.

## 10. All configured levels tell the same story

Do not generate level adaptations independently in ways that introduce different facts. The initial Alef, Alef Plus, and Bet versions—and any future configured versions—must share one frozen factual contract. Every HISTORY level preserves the principal actions, consequential change or turning point, and outcome; simpler levels may compress secondary dates, names, qualifiers, and context, but must not replace the story with generalities.

For CURRENT, the pipeline is: sources → factual brief → level adaptation with lexical units and contextual translations. For HISTORY, it is: compact sourced screening brief → duplicate review and selection → selected-only batched deep research → 8–12 ordered factual story beats → retold level adaptation with lexical units and contextual translations. For EVERYDAY and DIALOG, it is: scenario brief → level adaptation with lexical units and contextual translations. Within adaptation, Hebrew prose is written and proofread before it is segmented.

Alef may omit details and Bet may expand them, but central facts and events must remain consistent.

## 11. Generated-scenario diversity history

Generated everyday stories and dialogues must not repeat too frequently. Keep their scenario history in Git. For recent entries, retain the date, domain, scenario, main lexical themes, and target vocabulary. Consider approximately the previous 30 days when generating a new issue.

For a new complete issue, two EVERYDAY and two DIALOG stories are editorial targets, not validation requirements. The normal sourced target is four CURRENT and seven HISTORY stories. Discovery returns 12 CURRENT and 24 HISTORY screening candidates before filtering. Duplicate-reviewed but unselected HISTORY candidates remain in a reserve queue. Deep research normally uses one batched call for the selected seven; insufficient or invalid packs are replaced from the reserve queue and only those replacements enter the second and final batched attempt. A reserve is consumed at most once. Only after discovery, reserve replacement, and selected-only research may an unavailable or weak sourced slot be replaced by an EVERYDAY or DIALOG story. If both complete HISTORY research requests fail, generation aborts rather than silently publishing an all-generated substitute issue. The research prompt also receives compact date/type/category/ID/brief summaries from all issues in the previous three calendar days so CURRENT events, HISTORY subjects, EVERYDAY plots, and DIALOG situations are not repeated on consecutive days. Recent generated-scenario records are explicitly forbidden comparison data; an identical scenario ID or a renamed version with the same practical problem, interaction, and resolution must be discarded.

A same-day append generates only fully AI-generated EVERYDAY or DIALOG stories, in any mix. It does not generate CURRENT or HISTORY entries and does not enable web research. The output schema and pre-adaptation validation both enforce this restriction.

## 12. Generated-scenario domains

Example domains include supermarket, shopping, restaurant, café, food delivery, public transport, taxi, car, parking, petrol station, pharmacy, doctor, dentist, school, kindergarten, work, colleagues, customer support, phone call, WhatsApp, online shopping, delivery, returns, refunds, post office, package, bank, payment, credit card, apartment, rent, home repair, plumber, electrician, neighbours, weather, weekend plans, travel, hotel, airport, guests, cooking, cleaning, appointments, lateness, changed plans, lost or forgotten items, booking, queues, subscriptions, internet providers, mobile phones, home appliances, clothes, shoes, and family logistics. This list is extensible.

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

Show approximate reading time for each article and issue. A simple calculation based on Hebrew word count and level is sufficient. It should reflect that a learner reads more slowly than a native speaker and target approximately 40–50 minutes for the whole issue.

## 24. Sources and external images

CURRENT and archived HISTORY stories may store real publisher, title, and URL data when trustworthy canonical links are available. Missing, duplicate, or unverified links are discarded and an empty source list remains valid for archived content and CURRENT under the existing compatibility policy. A newly researched HISTORY story must retain at least two distinct canonical HTTPS content pages actually consulted during that research call. Every factual beat must cite one or more retained source URLs, and each retained source must support the pack; otherwise the pack is invalid and the subject is replaced or dropped before adaptation. EVERYDAY and DIALOG have no sources. Never create fictional links or present generated scenarios as news. The content type must be explicit in stored data.

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

A daily JSON file contains its date, available reading-level IDs, available translation-locale codes, and ordered stories. Each story contains its type, category, an English internal brief used for duplicate comparison, a source list that may be empty, an optional sourced-image object, its configured level variants, teaser, title, paragraphs, lexical annotations, and scenario metadata for EVERYDAY and DIALOG. Newly researched HISTORY stories retain 8–12 ordered English `storyBeats` as their source-supported factual contract. The public validator accepts 6–12 beats for compatibility with already published issues; archived stories created before this field remain valid without backfilling. If stored, beats are valid only on HISTORY and must be non-empty English strings. The richer beat IDs, narrative roles, required flags, and supporting URLs are private generation-time data and are not persisted. `index.json` lists available dates. `everyday-history.json` supports diversity checks for both generated types. Site configuration declares defaults and enabled locales; the reading-level configuration defines ordered adaptation bands; locale dictionaries contain interface copy.

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

CURRENT and HISTORY use real sources rather than scenario metadata. DIALOG reuses `everydayMeta` so old issue files remain compatible without a schema migration.

## 27. CURRENT generation

Inspect at least eight CURRENT candidate pages, filter out duplicates, politics, and unsuitable topics, evaluate practical spoken-language value, and select 3–5, normally 4. At least half should be Israeli or locally relevant when good material exists. Reject remote disasters, rescue missions, specialist science, and technology stories without direct relevance to ordinary life. Research, Hebrew adaptation, and annotation are separate model stages: research uses web search and freezes sourced/scenario metadata and briefs; adaptation receives those records as immutable input and returns plain Hebrew levels; annotation then segments and translates that frozen Hebrew without editing it. Do not select a collection of top headlines by default.

## 28. EVERYDAY generation

Read the recent scenario-history data, identify what has been used, remove overly similar ideas, normally select about two EVERYDAY situations, create scenario briefs, and adapt them into the issue's configured levels. Additional EVERYDAY stories may replace rejected sourced candidates. Prioritize reusable interaction with colleagues, managers, customers, neighbors, friends, strangers, and service workers. Mark every EVERYDAY story visibly as fully AI-generated in the selected interface language.

## 29. DIALOG generation

Aim for about two short dialogues for each new issue, with additional dialogues allowed to replace rejected sourced candidates. Use ordinary situations useful to a learner and their family, normally with two speakers and 8–12 short alternating turns. Store every turn as its own paragraph-array item so it appears on a separate line. Keep the exchange natural, simple, and practical across all configured levels. Reuse the scenario history to avoid recently repeated situations, and mark every DIALOG visibly as fully AI-generated.

## 30. HISTORY generation

Return 24 distinct compact HISTORY screening candidates from a substantially larger search and normally select seven. Classify each as `person`, `israeliIndustry`, `culture`, `event`, `place`, or `archaeology`; this internal field is used for selection and removed before publication. Require at least six person, six Israeli-industry, six culture, and four event candidates. Permit at most two place candidates and one archaeology candidate. The selected seven must contain at least two person, two Israeli-industry, two culture, and one event or exceptional place story, with at most one place and no archaeology. Favor concrete subjects that appear likely to support interesting stories, easy explanations, and useful ordinary language. They need not relate to the current date or current events. Do not spend the screening response on story beats. Retain duplicate-reviewed unselected HISTORY candidates as reserves, then deeply research only the selected subjects in one batched web call. A sufficient pack has 8–12 ordered beats, at least two actually consulted source pages, and required setup, action, turning-point, and outcome beats. Invalid packs are replaced from compatible reserves for at most one second batched attempt.

## 31. Facts and generation

Language adaptation must not freely invent details for real stories. A factual brief must precede all CURRENT versions; a compact brief and ordered factual beats must precede new HISTORY versions. HISTORY adaptation retells those beats rather than describing the source or offering generic commentary about the subject. Every level of a newly researched HISTORY story must report coverage of all required beat IDs and meet the configured `minimumWords`; failure retries the adaptation and then blocks publication. This stricter gate does not apply retroactively to archived HISTORY or to CURRENT, EVERYDAY, and DIALOG word counts. Never hallucinate details, repeat facts, or add filler to meet the minimum; a research pack too thin to support the required article must be rejected before adaptation.

## 32. OpenAI API

Use the OpenAI API for sourced discovery and selection, sourced semantic duplicate review, selected-HISTORY research, generated-scenario planning, level adaptation, lexical segmentation, and Russian and English translations. Use the current official SDK and a modern API. A normal issue first makes web-enabled CURRENT/HISTORY discovery requests that each return exactly 36 compact screening candidates rather than final stories. Every returned candidate batch then receives a separate no-web semantic duplicate review using only compact briefs and URLs before selection. One additional batched web-enabled call researches only the selected HISTORY subjects; at most one batched retry researches unresolved reserve replacements. A separate no-web EVERYDAY/DIALOG planning request fills the remaining issue slots, followed by one structured adaptation response per story.

Configure the model through `OPENAI_MODEL` and supply the key through `OPENAI_API_KEY`. Store the key only in a GitHub Actions secret or runtime environment. It must never enter Git, frontend assets, JSON content, HTML output, logs, or error messages.

In the target repository, both values are configured in the GitHub Actions environment named `daily-hebrew-reading`: `OPENAI_API_KEY` is an environment secret and `OPENAI_MODEL` is an environment variable. The issue-generation job must explicitly declare that environment before reading either value.

## 33. Prompts

Keep editorial rules separate from application code. Maintain six instruction groups:

- **Editorial:** CURRENT research, Language Value, political exclusions, interest, and HISTORY selection.
- **Deduplication:** binding semantic comparison of sourced candidates with prior-day and current-run sourced briefs.
- **Selected HISTORY research:** source-backed narrative beats for only the selected subjects and any reserve replacements.
- **Everyday:** realistic situations, diversity, recent topics, and useful conversational vocabulary.
- **Dialog:** short, natural family and daily-life conversations.
- **Adaptation:** Alef, Alef Plus, Bet, modern spoken Hebrew, target lengths, lexical units, RU/EN translation, and no filler.

## 34. Automation

A GitHub Actions workflow is configured to run daily at 01:37 UTC. Its first job logs the event name, event schedule expression, runner UTC time, run identity, actors, ref, head SHA, workflow ref/SHA, resolved target date, requested append count, and issue-existence decision. This diagnostic job must not receive OpenAI credentials. If the resolved issue already exists and no positive append was explicitly requested, the remaining jobs are skipped before Python setup, dependency installation, tests, secrets, or AI calls. When generation is needed, it validates the checked-out content and runs the unit tests before calling OpenAI so repository failures do not consume generation spend. It then generates a complete issue or explicit append, validates the changed content, updates generated-scenario history, writes the JSON, commits and pushes the content, builds the site, and deploys GitHub Pages. It must also support manual execution through `workflow_dispatch`, exposed in the repository's Actions tab as a **Run workflow** button.

The manual run accepts an optional target date, resolved as the current UTC date when omitted, and a requested number of additional stories from 0–10, defaulting to 0. When no issue exists for the target date, generation creates the normal complete issue regardless of the append input. When an issue already exists, zero is a no-op and a positive explicit value preserves every existing story and appends that many new stories instead of replacing the file. Append batches contain only EVERYDAY or DIALOG stories in any mix; the fixed new-issue counts do not apply. It recalculates issue metadata and navigation, updates generated-scenario history, validates the combined issue, and only then commits it.

Generation has four content-producing prompt stages plus a binding sourced-review gate. Sourced discovery receives only CURRENT/HISTORY editorial, search, source, and sourced-novelty rules. After every successful sourced search response, a separate no-web duplicate-review request receives only compact candidate, recent sourced, and already selected sourced records. Selected-HISTORY research receives only the chosen subjects or unresolved reserve replacements and uses web search. Generated planning receives only EVERYDAY/DIALOG scenario and generated-novelty rules and never uses web search. Adaptation receives only writing, dialogue-rendering, segmentation, translation, and configured level/locale rules for the frozen briefs, scenario metadata, and private HISTORY beat contracts. Generation keeps the configured `OPENAI_MODEL` for every stage and review.

Each planning stage receives only its relevant compact forbidden records from the existing issue and recent issues. Sourced discovery defines a CURRENT duplicate as the same central subject and underlying event, action, announcement, change, project, or outcome; equivalent URLs, alternate coverage, cosmetic rewrites, later status reports, continuing consequences, changed statistics, and minor follow-ups remain duplicates. For HISTORY, reuse of the same named primary subject—such as a street, building, archaeological site, institution, person, event, object, or custom—is a duplicate even when another source, period, excavation, archaeological layer, fact, or angle is used. Generated planning defines a duplicate by the practical problem or goal, interaction, and resolution; an identical recent scenario ID is always a duplicate, while sharing only a domain or vocabulary is allowed. Forbidden records are comparison data, never search suggestions or templates.

For the normal eleven sourced slots, each discovery attempt returns exactly 36 compact candidates containing an ID, type, category, internal history-family classification, factual English brief, and source metadata. Discovery never returns HISTORY story beats. Candidate IDs should be descriptive topic slugs, but Python defensively adds the issue date as an idempotent suffix before validation and publication so response-local placeholders such as `current-01` cannot collide with another day's story. When both types remain, discovery returns exactly 12 CURRENT and 24 HISTORY candidates and searches across the whole of Israel rather than defaulting to Jerusalem. CURRENT focuses on the target date and previous several days. HISTORY first considers worthwhile date-related facts, then prioritizes people, historic Israeli companies and manufacturing, culture, and concrete events without requiring an anniversary or current-news connection. The HISTORY pool contains at least six `person`, six `israeliIndustry`, six `culture`, and four `event` records; `place` is capped at two and `archaeology` at one. Python validates candidates individually in response order against recent records, already retained records, and earlier valid candidates from the same response. Candidate-specific URL, slug, brief, metadata, and duplicate failures remove only the affected candidate. Pool-count and history-family-mix failures are logged and merged into retry feedback but do not discard individually valid candidates. Deterministic family selection chooses the available final HISTORY mix before another discovery attempt fills remaining slots, and reviewed unselected HISTORY candidates become reserves. The internal family field is removed before adaptation and is never stored in issue JSON.

The separate LLM reviewer must classify every surviving candidate exactly once from its compact brief and URLs, comparing underlying events and named historical subjects rather than wording. Its duplicate verdicts are binding and removed candidates are never selected, reserved, adapted, or published. Missing, malformed, or failed review coverage fails closed by discarding the unreviewed batch, but does not fail publication: discovery retries, and generated stories fill any final shortfall. A retry must start a genuinely new worldwide replacement search; at least 27 of its 36 candidates should be outside Israel and span at least six countries or regions, while preserving required Israeli-industry coverage. It must not return alternate coverage, translations, updates, or renamed versions of rejected stories. All editorial, safety, source, and novelty rules remain active.

After selection, one batched web request researches all chosen HISTORY subjects. Each requested ID must appear exactly once. Valid partial results are retained; malformed, missing, duplicate, unsupported, or explicitly insufficient packs remain unresolved. Every sufficient pack contains 8–12 unique English beats with stable IDs, narrative roles, required flags, and supporting URLs. Required beats collectively cover setup, action, turning point, and outcome. Returned source URLs must be actual pages consulted by web search, and every beat's supporting URLs must be a non-empty subset of the retained verified source list. On the first attempt, each unresolved selected subject is replaced in place by one compatible reviewed reserve when available. Only unresolved replacements enter the second and final batched research request, and each reserve can be consumed once. After research, generated planning fills any issue shortfall with EVERYDAY and DIALOG stories. Generated duplicates are removed and only the remaining slots are retried. Type counts are editorial targets, not publication-blocking quotas, and a final shortfall does not by itself fail publication when usable unique stories remain.

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

Include sample issue content so the frontend can be tested without an OpenAI API key. Existing archived samples remain valid without DIALOG backfilling; newly generated issues use the four-type mix. Do not present invented current news as factual reporting.

## 39. User experience

The product should feel like a small daily magazine for a full commute. A day page shows the date, story count, approximate reading time, a level selector, and concise cards for locally relevant CURRENT, practical EVERYDAY, natural DIALOG, and relatable HISTORY entries. Opening one should provide a calm reading experience followed by a simple move to the next.

## 40. Product philosophy

The experience is a daily collection of short, interesting stories, real-life situations, and ordinary conversations through which the reader gradually understands more normal contemporary Hebrew. Language value wins over news importance; natural contemporary Hebrew wins over newspaper style; repetitive generated situations are replaced; and a text that would require filler is shortened.

## 41. Required MVP delivery

Deliver a complete MVP containing daily generation and safe same-day appends; CURRENT research and selection; HISTORY research; EVERYDAY and DIALOG generation with repetition protection; the three initial configurable Hebrew levels; extensible interface and translation locales; lexical annotation; Russian and English translations; Git-based content storage; validation; optional externally linked source images; static-site building; home, archive/day, and separate article pages; level and locale switches; hover/tap translations; sources; previous/next navigation; GitHub Actions; GitHub Pages deployment; sample content; basic tests; and a README.

After implementation, run tests, validate content, build the static site, inspect the principal pages, and fix discovered defects. The handoff report must state what was implemented, major decisions, successful checks, and manual GitHub configuration required from the repository owner.

## 42. Visual design approval gate

Before frontend implementation begins, prepare 3–4 distinct visual directions for owner review. Each direction must demonstrate the complete page family—home, archive, day, and article—as well as representative desktop and mobile states and the translation popover. The owner chooses a direction and may request adjustments; frontend work begins only after that approval.

The owner selected Direction 1, **Jerusalem Journal**, on 4 September 2026. The production frontend should carry forward its restrained editorial typography, warm paper background, deep teal structure, coral accent, fine rules, square controls, calm reading width, and source-image treatment. The prototype is a visual reference rather than production markup.
