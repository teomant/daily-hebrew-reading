# Everyday-story instructions

Plan fully AI-generated EVERYDAY scenarios. This phase creates only English briefs and scenario metadata; do not research factual stories, use web sources, write Hebrew adaptations, segment text, or translate anything. Create realistic miniature stories about adult life in Israel, not classroom phrase exchanges. The supplied domain pools mix essential situations, routine life, and worthwhile experiences. Each story should give a learner reusable Hebrew for a comparable need or experience: describe what happened or what they are doing, ask a useful question, understand or clarify a reply, make a choice, and see an outcome. A story needs a concrete situation, interaction, action, and result. Interactions may be with a cashier, clerk, doctor, landlord, service worker, colleague, neighbor, friend, or family member. Explore broadly across the supplied pools; the user's examples are illustrative, not an exhaustive list.

Distinguish domain from scenario. Use the canonical domain values supplied in the request and give each story in the current issue a different domain. A domain may return on another day, but do not repeat a recently used situation with renamed characters. Treat every supplied recent scenario record as forbidden comparison data. An identical `scenario` value is automatically a duplicate and must never be returned. A renamed scenario is still a duplicate when the practical problem or goal, interaction, and resolution are substantially the same. Exclude the supplied recent scenarios. Repetition of frequent language is useful; repetition of plots is not.

For both EVERYDAY and DIALOG, compare plot patterns across all supplied recent full stories and SHORTS items before choosing new situations.
Prefer activities and relationships that appear less often in those records, within the supplied domains and pool targets.
Do not build the batch around people asking staff for instructions and confirming the answer.
Vary what people actually do: cooperate on a task, negotiate different preferences, offer or decline help, explain a mistake, try something themselves, or respond to an unexpected result.
These are examples, not a fixed rotation.
Essential tasks can involve initiative and cooperation as well as service problems.
If removing names, locations, and objects leaves the same goal, action, and outcome as another story, choose a different plot.
A different domain or format alone does not make a familiar situation fresh.

Vary the task and interaction, not only the object or location. A delay, queue, injury, billing error, missing document, broken appliance, or service problem is worthwhile when the story teaches a concrete response. Ordinary preventive tasks are useful too. Cooking a meal, taking a trip, visiting an event, or spending time outdoors can also make a good story when people actually do something, encounter a concrete detail or choice, and reach an outcome. A problem is not required. Avoid empty premises where friends only decide to start a hobby, make a shared album, or choose an activity. Across one batch, vary the people involved, what they say or do, the development, and the outcome; avoid repeated “phone, wait, everything is fixed” plots.

These no-web stories are language practice, not current service guides. For healthcare, banking, taxes, government documents, insurance, benefits, and pricing, do not invent Israeli rules, exact fees or rates, deadlines, eligibility, coverage, diagnoses, or entitlements. Ordinary fictional details are welcome: what someone brought, noticed, misunderstood, tried, chose, or did. Give the interaction an actual answer and visible action without claiming a universal rule. Refer to official instructions only when the particular situation needs them; this is not the default ending. A character may remain uncertain about an official decision while still resolving an ordinary part of the task. Do not make the plot stall at “check online” without a useful interaction.

Favor natural constructions such as עדיין לא, כבר, עוד מעט, בערך, לא הספקתי, לא שמתי לב, שכחתי, אמרו לי ש, הבטיחו לי, אני כבר בדרך, אפשר להחליף, כדאי, עדיף, אין לי זמן, מתי בערך, תוך כמה זמן, בסוף החלטתי, נראה לי, לא נורא, אין בעיה, אין צורך, זה לא משתלם, מה אפשר לעשות, נשאר, נגמר, and חסר when they fit naturally. Include realistic requests, clarifications, polite disagreement, explanations, reactions, and changes of plan—not only narration.

Across the batch, vary how events develop: a discovery, a preference, a misunderstanding, cooperation, a small setback, or a choice can move a story forward. Do not make every character ask permission or every ending summarize what the character learned. Keep roles and the direction of actions consistent: who paid whom, who owns the object, and who can answer the question.

Make each scenario brief adaptation-ready by laying out 4–5 distinct story beats: the initial situation, the interaction or first attempt, a useful clarification or complication, the decision or action, and the practical outcome. Give the later adaptation enough concrete but ordinary material for developed paragraphs without filler. Provide the brief, domain, stable snake_case scenario name, lexical themes, and target vocabulary, and set `dialogSpeakers` to an empty list. EVERYDAY stories never have sources or images and must never be presented as news.

Record `everydayMeta.storyPattern` as four compact English phrases: goal, relationship, interaction, and outcome.
Describe the pattern without character names, places, or replaceable objects.
Compare these fields with recent full stories and individual SHORTS as well as within this batch.
Prefer less-used relationships, developments, and outcomes; sharing useful vocabulary is welcome.
Do not make essential, routine, and experience domains all follow the same ask/check/confirm sequence.
