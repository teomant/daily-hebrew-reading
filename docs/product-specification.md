# Hebrew Reading Magazine — MVP Product Specification

Status: approved product requirements, translated from the Russian specification supplied by the repository owner on 2026-09-04.

This document describes a fully working MVP of a static website for daily reading in modern spoken Hebrew. The product is for learners who want to read contemporary, natural Hebrew regularly but are not yet ready for books or difficult newspaper articles.

The core idea is to give the reader a small daily issue containing 20–30 minutes of short, interesting material and realistic everyday stories. This is neither a conventional news site nor a textbook. News supplies interesting stories and new vocabulary; everyday texts systematically cover language people need in real life.

The primary product principle is to select and create material according to what is interesting to read and useful for learning contemporary Hebrew, not according to what is considered the day's most important news.

## 1. Daily issue

A new issue is generated automatically every day. A typical issue contains:

- 5–7 real, recent stories;
- 3–4 purpose-written everyday stories;
- 1 historical story.

This normally produces 9–11 stories, but the count is deliberately flexible. If there are too few good CURRENT stories, publish fewer of them and add a strong EVERYDAY story. If there are many genuinely strong stories, the issue may be slightly larger. Never fill a quota with weak material.

The target reading time is approximately 20–30 minutes. Prefer a larger number of short articles over a few long ones.

## 2. Content types

The three content types are CURRENT, EVERYDAY, and HISTORY.

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

### HISTORY

A real historical story, normally one per issue. It may be an “on this day” item, an event that occurred around the current date in a previous year, or a story from Israeli history, world history, science, technology, transport, culture, food, business, a famous success or failure, an invention, or another unusual event.

It must be a story rather than a bare date. “The Edsel was introduced on 4 September 1957” is insufficient. A useful article would explain that Ford invested heavily in a new model, expected and advertised a major success, but buyers reacted very differently from the company's expectations.

HISTORY must have real sources. If no interesting event fits a particular date, do not force an uninteresting date connection.

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

Approximately 80–120 words, with modest flexibility. This targets a learner near the end of beginner Alef/A1.1 who can already decode Hebrew text, not an absolute beginner learning the alphabet. Use short sentences, simple structure, frequent vocabulary, few complex subordinate clauses, and a clear sequence of events. The result is simple adult Hebrew, not children's prose.

### Alef Plus — א+

Approximately 120–170 words, corresponding approximately to advanced Alef/A1.2. It may use more past tense, cause and effect, natural connectors, simple subordinate clauses, more fixed expressions, and somewhat richer vocabulary.

### Bet — ב

Approximately 160–220 words, occasionally up to 250 when the story genuinely requires it, corresponding approximately to Bet/A2. This is reasonably natural contemporary Hebrew and may include more detail, causes, comparisons, reactions, and conversational constructions, including common colloquial expressions, without becoming dense newspaper prose.

## 8. Do not pad articles

Word counts are guidelines, not goals. Do not lengthen an article through repetition, empty introductions, generic conclusions, unnecessary adjectives, invented details, or artificially complex phrasing. A short, good text is better than a longer text with filler.

## 9. Hebrew style

Use modern spoken Israeli Hebrew: language in which a contemporary Israeli might naturally tell or explain something to another person.

Avoid biblical or religious language, elevated literary prose, bureaucracy, dense newspaper style, and needlessly formal constructions. For example, prefer אחרי מה שקרה, העירייה הודיעה שהיא עוצרת את הפרויקט בינתיים over בעקבות ההתפתחויות הודיעה העירייה על השהיית הפרויקט. At Alef, simplify further to העירייה החליטה לעצור את הפרויקט עכשיו.

The MVP does not need niqqud. Consequently, even the Alef band assumes the reader has moved beyond initial alphabet and decoding instruction.

## 10. All configured levels tell the same story

Do not generate level adaptations independently in ways that introduce different facts. The initial Alef, Alef Plus, and Bet versions—and any future configured versions—must share one brief.

For CURRENT and HISTORY, the pipeline is: sources → factual brief → all configured level adaptations. For EVERYDAY, it is: scenario brief → all configured level adaptations.

Alef may omit details and Bet may expand them, but central facts and events must remain consistent.

## 11. EVERYDAY diversity history

Generated everyday stories must not repeat too frequently. Keep the history of EVERYDAY topics in Git. For recent stories, retain the date, domain, scenario, main lexical themes, and target vocabulary. Consider approximately the previous 30 days when generating a new issue.

## 12. EVERYDAY domains

Example domains include supermarket, shopping, restaurant, café, food delivery, public transport, taxi, car, parking, petrol station, pharmacy, doctor, dentist, school, kindergarten, work, colleagues, customer support, phone call, WhatsApp, online shopping, delivery, returns, refunds, post office, package, bank, payment, credit card, apartment, rent, home repair, plumber, electrician, neighbours, weather, weekend plans, travel, hotel, airport, guests, cooking, cleaning, appointments, lateness, changed plans, lost or forgotten items, booking, queues, subscriptions, internet providers, mobile phones, home appliances, clothes, shoes, and family logistics. This list is extensible.

## 13. Do not repeat scenarios

Domain and scenario are different. The restaurant domain can recur later, but articles should not repeat nearly identical plots. Different restaurant scenarios include an unavailable dish, arriving without a reservation, waiting too long, receiving the wrong dish, splitting the bill, changing a reservation, or recovering an item left behind.

As a soft guideline, avoid using the same principal domain several times in one week and avoid repeating the same scenario for several weeks. The purpose is to prevent the feeling that only the names changed in a recently read story.

## 14. Vocabulary may repeat

Frequent vocabulary does not need to be new every day; repetition is useful. Words such as להגיע, לחכות, לבחור, כדאי, לבדוק, להזמין, להשתמש, and לשלם may recur. Avoid repeating plots, not language.

## 15. Everyday vocabulary planning

EVERYDAY stories should gradually cover varied conversational vocabulary. One day may emphasize waiting, changing plans, requests, and replacement; another may emphasize comparison, payment, clarification, and mistakes. Do not build a complex curriculum system. Recent scenarios and lexical themes are enough.

## 16. Lexical units

The principal interactive feature is translation of words and expressions. Hebrew text must be segmented into useful lexical units, not merely split on spaces. A unit can be a single word, a fixed expression, a multi-word construction, or a proper noun.

For example, מזג אוויר is one unit translated as “погода” in Russian and “weather” in English; שם לב is one unit translated as “обратить внимание” and “notice / pay attention”; בסופו של דבר is one unit translated as “в итоге / в конце концов” and “in the end / eventually.” Do not mechanically split fixed expressions when doing so makes comprehension worse.

## 17. Translation coverage

Almost all main Hebrew text must be interactive so a reader can select nearly any unfamiliar word or expression. For each meaningful lexical unit, store the Hebrew text, a translation map keyed by stable locale code, and its type. The initial translation locales are `ru` and `en`, but content rendering and validation must use each issue's configured translation locales rather than fixed Russian and English fields.

The MVP needs these types: `word`, `expression`, `properNoun`, and `separator`. Separators need no translation.

The MVP does not need roots, binyanim, conjugation, transliteration, niqqud, word frequency, or grammatical analysis.

## 18. Translation tooltip or popover

On desktop, hover reveals a translation and keyboard focus must provide the same access. On mobile, tapping reveals it and tapping outside closes it. The reader chooses one available translation language and sees only that language. The initial choices are RU and EN. The popover must not move the text or break the layout.

The site interface itself also has an independent language selector, initially with Russian and English options. Interface language changes navigation, labels, categories, dates, reading-time text, source labels, and accessibility text; it does not translate the Hebrew article content. Interface strings live in locale dictionaries keyed by locale code, and UI components must not contain language-specific branching. Persist the selected interface language in `localStorage`.

## 19. Site structure and URLs

The site is fully static. Navigation follows Home → Day → Article. Example paths are `/`, `/2026-09-04/`, and `/2026-09-04/sheep-save-glaciers/`. Every article has its own page.

## 20. Home page

The home page shows the latest available issue, its date, story count, approximate reading time, story list, and access to earlier days or the archive. It is not a large marketing landing page; its purpose is to let the reader start quickly.

## 21. Day page

The page for a date is that issue's table of contents. It shows the date, story count, approximate total reading time, and article cards. Each card contains the Hebrew title, category, short teaser, and approximate reading time, and links to the article page.

## 22. Article page

An article page contains a link back to the issue, date, category, title, reading time, level selector (`א`, `א+`, `ב`), translation-language selector (`RU`, `EN`), interface-language selector (`RU`, `EN`), text with lexical popovers, sources for CURRENT and HISTORY, and previous/next article navigation.

Persist the selected level, translation language, and interface language between pages using `localStorage` for the MVP. Translation language and interface language are separate preferences.

## 23. Reading time

Show approximate reading time for each article and issue. A simple calculation based on Hebrew word count and level is sufficient. It should reflect that a learner reads more slowly than a native speaker and provide useful estimates such as 2 minutes, 3 minutes, or approximately 24 minutes for the whole issue.

## 24. Sources and external images

CURRENT and HISTORY require real sources. Store publisher, title, and URL. EVERYDAY has no sources. Never create fictional links or present an EVERYDAY story as news. The content type must be explicit in stored data.

A CURRENT or HISTORY story may also have one optional image linked directly from one of its original source articles. Store the HTTPS image URL, the source article URL, publisher or credit, localized alt text, and an HTTPS usage-rights/policy URL with a short factual label. The generator may return an image only when the image, source, and policy URLs all appear in its actual web-research results; otherwise it returns no image. The card and article page may display it with source attribution and links to the original article and usage policy. Do not download or commit third-party images for the MVP. If the URL is missing, rejected, or later stops loading, render the story normally without an image or broken layout. Images are optional and must only be used when the applicable source and usage rights allow embedding; generation must not invent ownership or licensing information. EVERYDAY stories do not automatically receive sourced images.

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

A daily JSON file contains its date, available reading-level IDs, available translation-locale codes, and ordered stories. Each story contains its type, category, sources when required, an optional sourced-image object, its configured level variants, teaser, title, paragraphs, lexical annotations, and EVERYDAY metadata when applicable. `index.json` lists available dates. `everyday-history.json` supports diversity checks. Site configuration declares defaults and enabled locales; the reading-level configuration defines ordered adaptation bands; locale dictionaries contain interface copy.

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

CURRENT and HISTORY use real sources rather than EVERYDAY metadata.

## 27. CURRENT generation

Find more candidates than the issue needs, filter out politics and unsuitable topics, evaluate Language Value, select the best 5–7, and create a factual brief. Research/selection and adaptation are separate model phases: the first phase uses web search and freezes sourced/scenario metadata and briefs; the second receives those records as immutable input and may return only level adaptations keyed by the same story IDs. Do not select a collection of top headlines by default.

## 28. EVERYDAY generation

Read the recent everyday-history data, identify what has been used, propose several new scenarios, remove overly similar ideas, select 3–4, create scenario briefs, and adapt them into the issue's configured levels.

## 29. HISTORY generation

Find several potential historical stories and select the one that is most interesting, easiest to explain, and richest in useful language. Gather facts and sources before writing the adaptations.

## 30. Facts and generation

Language adaptation must not freely invent details for real stories. A factual brief must precede all CURRENT and HISTORY level versions. If evidence is limited, make the article shorter. Never hallucinate details to reach a length target.

## 31. OpenAI API

Use the OpenAI API for research and selection, factual and scenario briefs, level adaptation, lexical annotation, and Russian and English translations. Use the current official SDK and a modern API. A normal issue uses a web-enabled structured research response followed by a separate structured adaptation response, so level prose cannot rewrite the frozen brief or source metadata.

Configure the model through `OPENAI_MODEL` and supply the key through `OPENAI_API_KEY`. Store the key only in a GitHub Actions secret or runtime environment. It must never enter Git, frontend assets, JSON content, HTML output, logs, or error messages.

In the target repository, both values are configured in the GitHub Actions environment named `daily-hebrew-reading`: `OPENAI_API_KEY` is an environment secret and `OPENAI_MODEL` is an environment variable. The issue-generation job must explicitly declare that environment before reading either value.

## 32. Prompts

Keep editorial rules separate from application code. At minimum, maintain three instruction groups:

- **Editorial:** CURRENT research, Language Value, political exclusions, interest, and HISTORY selection.
- **Everyday:** realistic situations, diversity, recent topics, and useful conversational vocabulary.
- **Adaptation:** Alef, Alef Plus, Bet, modern spoken Hebrew, target lengths, lexical units, RU/EN translation, and no filler.

## 33. Automation

A GitHub Actions workflow runs daily at 06:00 UTC. It generates a complete issue, validates it, updates EVERYDAY history, writes the JSON, commits and pushes the content, builds the site, and deploys GitHub Pages. It must also support manual execution through `workflow_dispatch`, exposed in the repository's Actions tab as a **Run workflow** button.

The manual run accepts an optional target date, resolved as the current UTC date when omitted, and a requested number of additional stories, defaulting to 3. When no issue exists for the target date, generation creates the normal complete issue. When an issue already exists, generation preserves every existing story and appends the requested new stories instead of replacing the file. It recalculates issue metadata and navigation, updates EVERYDAY history, validates the combined issue, and only then commits it.

Append generation must use existing slugs, source URLs, story topics, and recent EVERYDAY scenarios as exclusions. It must reject duplicate or near-duplicate additions. Generation runs are serialized so simultaneous scheduled or manual invocations cannot race and overwrite one another. A failed append leaves the existing issue unchanged.

The repository's default branch is `master`. An ordinary push to `master` does not generate an issue; it only validates, builds, and deploys the existing content. Generation commits also target `master`.

## 34. GitHub Pages

The target repository is `https://github.com/teomant/daily-hebrew-reading`, and the target project-site URL is `https://teomant.github.io/daily-hebrew-reading/`. Asset paths, content paths, links, and article URLs must all respect the `/daily-hebrew-reading/` base path.

## 35. Technology constraints

Keep the MVP simple. Prefer Python, HTML, CSS, vanilla JavaScript, JSON, GitHub Actions, and GitHub Pages. Do not add a database, backend, authentication, Docker, Kubernetes, Next.js, React, external hosting, or a CMS without a demonstrated need and explicit approval. The delivered site is entirely static.

## 36. Reliability

Before publishing generated content, validate at least:

- valid JSON;
- an ID and slug for every story;
- every level declared by the issue;
- non-empty text;
- required translations for lexical units;
- sources for CURRENT and HISTORY;
- domain and scenario for EVERYDAY;
- no duplicate slugs or duplicate source stories;
- optional image metadata uses safe HTTPS URLs, refers to one of the story's source articles, includes an independently researched usage-rights/policy URL and factual rights label, and contains attribution plus alt text for the issue's translation locales.

If generation fails, do not publish a partial issue or damage earlier content. The existing site must remain available and the workflow must fail visibly.

## 37. Sample content

Include a sample issue so the frontend can be tested without an OpenAI API key. It must demonstrate CURRENT, EVERYDAY, HISTORY, the three initial configured levels, lexical popovers, a day page, and article pages. Do not present invented current news as factual reporting.

## 38. User experience

The product should feel like a small daily magazine. A day page might show a date, “10 stories · about 25 minutes,” a level selector, and concise cards such as a science story about whether sheep's wool can help glaciers or an everyday story about a delayed delivery. Opening a story should provide a calm reading experience followed by a simple move to the next story.

## 39. Product philosophy

The experience is a daily collection of short, interesting stories and real-life situations through which the reader gradually understands more normal contemporary Hebrew. Language value wins over news importance; natural contemporary Hebrew wins over newspaper style; a repetitive EVERYDAY story is replaced; weak CURRENT supply is balanced with stronger EVERYDAY material; and a text that would require filler is shortened.

## 40. Required MVP delivery

Deliver a complete MVP containing daily generation and safe same-day appends; CURRENT research and selection; HISTORY research; EVERYDAY generation and repetition protection; the three initial configurable Hebrew levels; extensible interface and translation locales; lexical annotation; Russian and English translations; Git-based content storage; validation; optional externally linked source images; static-site building; home, archive/day, and separate article pages; level and locale switches; hover/tap translations; sources; previous/next navigation; GitHub Actions; GitHub Pages deployment; sample content; basic tests; and a README.

After implementation, run tests, validate content, build the static site, inspect the principal pages, and fix discovered defects. The handoff report must state what was implemented, major decisions, successful checks, and manual GitHub configuration required from the repository owner.

## 41. Visual design approval gate

Before frontend implementation begins, prepare 3–4 distinct visual directions for owner review. Each direction must demonstrate the complete page family—home, archive, day, and article—as well as representative desktop and mobile states and the translation popover. The owner chooses a direction and may request adjustments; frontend work begins only after that approval.

The owner selected Direction 1, **Jerusalem Journal**, on 4 September 2026. The production frontend should carry forward its restrained editorial typography, warm paper background, deep teal structure, coral accent, fine rules, square controls, calm reading width, and source-image treatment. The prototype is a visual reference rather than production markup.
