# Separate reading editions

Each issue has independent Alef, Alef Plus, and Bet editions.
The normal target is twelve pages per edition.
An article belongs to one edition and cannot change level in place.

## Reading profiles

| Edition | Approximate level | Writing profile |
|---|---|---|
| Alef — א | A1.1 | Familiar concrete words, explicit subjects, simple questions, and mainly single-clause sentences. Everyday fiction mainly uses present tense. Sourced articles retain the correct time. |
| Alef Plus — א+ | A1.2 | Common past forms alongside present tense, useful expressions, short connected sentences, and clear sequences. Future tense is not the teaching focus. |
| Bet — ב | A2 | Present, past, and future forms, precise everyday words, simple conditions and relative clauses, comparisons, reasons, and plans. Avoid dense or formal prose. |

The mapping follows the [Hebrew University descriptors](https://overseas.huji.ac.il/wp-content/uploads/2019/07/ENGLISH-EVAL.pdf).
The [Alef syllabus](https://overseas.huji.ac.il/wp-content/uploads/2023/07/Syllabus-Level-Aleph-2023-REVISED.pdf) includes present and past tense.
The [Bet syllabus](https://overseas.huji.ac.il/wp-content/uploads/2023/01/Syllabus-Level-Bet-2022.pdf) adds future tense.
These are editorial targets, not certification or a placement test.
The site assumes that readers can decode unpointed Hebrew.
No word-count target or automatic difficulty gate is added.

## Topic selection and writing

Select topics once using the existing weekday lists and recent-topic exclusions.
Research CURRENT and HISTORY subjects once.
Each sourced edition keeps the same subject, factual brief, sources, and required historical facts.
Optional detail and explanations may differ.
Simplification must preserve attribution and uncertainty.
Do not invent conversations in sourced articles.

Write each topic separately for each configured level.
Each writing request receives only that level's guidance and response fields.
EVERYDAY, DIALOG, and SHORTS may use different fictional actions, complications, and outcomes within the selected topic.
Keep the topic domain and the planned dialogue participants and roles.
Return the actual English brief and scenario metadata for the finished fictional article.
Record each edition's scenario in repetition history.
Past archived records without an edition remain valid and continue to inform topic selection.

Keep the existing bounded content retries and annotation repair for each article.
If writing fails for one edition, retain successful articles in other editions.
SHORTS collects up to eleven successful items separately in each edition.
A VERBS page requires all ten assigned items in that edition.
An incomplete VERBS edition does not remove another edition's complete page.
No new paid review, research stage, model, or deployment step is introduced.
Usage logs include the edition in writing phases and retain cost estimates.

## Stored format

Issue schema version 2 contains `date`, optional `generatedAt`, `availableLevels`, `translationLocales`, and `editions`.
The keys of `editions` exactly match `availableLevels`.
Each edition contains an ordered `stories` list.
Each article stores its existing metadata, a stable `topicId`, and one `content` object with lexical `title`, `teaser`, and `paragraphs` arrays.
It does not store a `levels` map.
The edition key identifies the article's reading level.
The combination of date, edition, and slug identifies its page.
Linked editions share a topic ID, but their fictional briefs and wording may differ.
Sources and research metadata for a shared sourced topic must agree.

`index.json` schema version 2 lists dates newest first.
Each date contains an `editions` map with `storyCount` and `readingMinutes` for each available edition.
Counts refer to pages in that edition, including grouped SHORTS and VERBS pages.
An edition with no successful articles is omitted.
Its home page can still show its latest earlier issue.

`src/editions.py` supplies conversion, topic records, index construction, and a single-edition view for existing lexical checks and templates.
The internal view uses a singleton `levels` map.
It does not expose other editions' article text to the browser.
Schema-1 input remains readable for legacy fixtures and migration.
New generation always writes schema 2.
Successful appends preserve all existing article content and add new topics per edition.

## Routes and preferences

- Edition homes: `/alef/`, `/alef-plus/`, and `/bet/`.
- Edition archives: `/{edition}/archive/`.
- Dated editions: `/{edition}/YYYY-MM-DD/`.
- Articles: `/{edition}/YYYY-MM-DD/{slug}/`.

All paths support the configured GitHub Pages base path.
CSS and JavaScript URLs include a version derived from each file's content.
Changed assets receive new URLs so browsers do not combine updated pages with cached styles or scripts from an earlier release.
Home, archive, and day edition controls are ordinary navigation links.
Day controls list only editions available on that date.
An article displays a fixed edition badge and retains the translation-language controls.
Brand, archive, back, previous, next, and random navigation stay in the edition.
Random selection excludes the current article.

The old root, archive, day, and article URLs remain compatibility pages.
They select an available destination using the saved reading preference, then the configured default, then the first available edition.
Ordinary destination links work without JavaScript.
A directly opened edition URL always determines its level, regardless of saved preferences.
Interface and translation languages remain separate saved preferences.
Blocked browser storage does not prevent reading.

## Offline migration

Preview the migration:

```bash
python -m src.migrate_editions
```

Apply it:

```bash
python -m src.migrate_editions --write
```

The script validates the repository and all converted issues before writing.
It uses the existing transactional writer with rollback on write errors.
It rebuilds the per-edition index and leaves scenario history unchanged.
Running it again makes no changes.
It copies existing lexical units, translations, metadata, images, sources, and grouped items without rewriting them.
Old wording defects therefore remain in the archive.
No API call is made.

The November 12, 2026 issue and its index/history entries were removed before this migration at the owner's request.
The date is ready for a fresh generation after this code is published.
Local verification does not trigger paid generation or deployment.
