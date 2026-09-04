from __future__ import annotations

import argparse
import html
import json
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

from .common import (
    ROOT,
    ensure_base_path,
    issue_minutes,
    load_level_config,
    load_locales,
    load_site_config,
    read_json,
    site_url,
    story_minutes,
    units_need_space,
    units_text,
)
from .validation import validate_repository


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def json_script(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def format_date(value: str, locale: str = "") -> str:
    del locale
    return value


def minutes_label(minutes: int, locale: str, copy: dict[str, str]) -> str:
    del locale, copy
    return str(minutes)


def issue_level(issue: dict[str, Any], site: dict[str, Any]) -> str:
    preferred = site["defaultReadingLevel"]
    return preferred if preferred in issue["availableLevels"] else issue["availableLevels"][0]


def image_alt(image: dict[str, Any], locale: str) -> str:
    return image["alt"].get(locale) or next(iter(image["alt"].values()))


def render_units(units: list[dict[str, Any]], interactive: bool = False) -> str:
    rendered: list[str] = []
    for index, unit in enumerate(units):
        if index and units_need_space(units[index - 1], unit):
            rendered.append(" ")
        text = esc(unit["text"])
        if unit["type"] == "separator" or not interactive:
            rendered.append(text)
            continue
        translations = esc(json.dumps(unit["translations"], ensure_ascii=False))
        rendered.append(
            f'<button class="lexeme" type="button" data-unit-type="{esc(unit["type"])}" '
            f'data-translations="{translations}">{text}</button>'
        )
    return "".join(rendered)


def shell(
    *,
    title: str,
    body: str,
    page: str,
    site: dict[str, Any],
    levels: list[dict[str, Any]],
    locales: dict[str, dict[str, str]],
    payload: dict[str, Any] | None = None,
) -> str:
    base = ensure_base_path(site["basePath"])
    default_locale = site["defaultInterfaceLocale"]
    copy = locales[default_locale]
    locale_options = "".join(
        f'<option value="{esc(code)}">{esc(code.upper())}</option>' for code in site["interfaceLocales"]
    )
    runtime = {
        "site": site,
        "levels": levels,
        "locales": locales,
        "page": page,
        "payload": payload or {},
    }
    return f"""<!doctype html>
<html lang="{esc(default_locale)}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="color-scheme" content="light">
  <title>{esc(title)} · {esc(site['siteName'])}</title>
  <link rel="stylesheet" href="{esc(site_url('assets/styles.css', base))}">
</head>
<body data-page="{esc(page)}">
  <a class="skip-link" href="#main" data-i18n="accessibility.skipContent">{esc(copy['accessibility.skipContent'])}</a>
  <header class="site-header">
    <a class="brand" href="{esc(base)}"><span class="brand-mark">א</span><span><strong>{esc(site['siteName'])}</strong><small data-i18n="siteTagline">{esc(copy['siteTagline'])}</small></span></a>
    <nav class="site-nav" aria-label="{esc(copy['accessibility.primaryNavigation'])}"><a href="{esc(base)}" data-i18n="nav.today">{esc(copy['nav.today'])}</a><a href="{esc(site_url('archive/', base))}" data-i18n="nav.archive">{esc(copy['nav.archive'])}</a><label class="locale-control"><span class="sr-only" data-i18n="accessibility.interfaceLanguage">{esc(copy['accessibility.interfaceLanguage'])}</span><select id="interface-locale">{locale_options}</select></label></nav>
  </header>
  <main id="main">{body}</main>
  <footer class="site-footer"><strong>{esc(site['siteName'])}</strong><span data-i18n="footer.schedule">{esc(copy['footer.schedule'])}</span><a href="{esc(site_url('archive/', base))}" data-i18n="nav.archive">{esc(copy['nav.archive'])}</a></footer>
  <script id="dhr-data" type="application/json">{json_script(runtime)}</script>
  <script src="{esc(site_url('assets/app.js', base))}" defer></script>
</body>
</html>"""


def level_controls(issue: dict[str, Any], levels: list[dict[str, Any]], label_key: str) -> str:
    available = set(issue["availableLevels"])
    buttons = "".join(
        f'<button type="button" data-level="{esc(level["id"])}" title="{esc(level["name"])} · {esc(level["approximateCefr"])}">{esc(level["label"])}</button>'
        for level in levels if level["id"] in available
    )
    return f'<div class="level-control"><span data-i18n="{label_key}"></span><div>{buttons}</div></div>'


def story_kind(story: dict[str, Any], copy: dict[str, str]) -> str:
    return f"{copy.get('category.' + story['category'], story['category'])} · {copy['type.' + story['type']]}"


def story_card(story: dict[str, Any], index: int, issue: dict[str, Any], site: dict[str, Any], levels: list[dict[str, Any]], copy: dict[str, str], lead: bool = False) -> str:
    level_id = issue_level(issue, site)
    level = story["levels"][level_id]
    url = site_url(f"{issue['date']}/{story['slug']}/", site["basePath"])
    image = ""
    if lead and story.get("image"):
        img = story["image"]
        image = f'<figure class="card-image"><img src="{esc(img["url"])}" alt="{esc(image_alt(img, site["defaultInterfaceLocale"]))}" loading="lazy" referrerpolicy="no-referrer"><figcaption>{esc(img["credit"])} · <a href="{esc(img["sourceUrl"])}" rel="noopener noreferrer" target="_blank" data-i18n="article.imageSource">{esc(copy["article.imageSource"])}</a> · <a href="{esc(img["rightsUrl"])}" rel="noopener noreferrer" target="_blank" data-i18n="article.imageRights">{esc(copy["article.imageRights"])}</a></figcaption></figure>'
    css = "story-card lead-card" if lead else "story-card"
    if image:
        css += " has-image"
    return f'''<article class="{css}" data-story-index="{index}">{image}<div class="card-copy"><span class="story-kind" data-story-kind>{esc(story_kind(story, copy))}</span><h2 dir="rtl" data-story-title>{render_units(level["title"])}</h2><p dir="rtl" data-story-teaser>{render_units(level["teaser"])}</p><footer><span data-story-minutes>{esc(minutes_label(story_minutes(story, level_id, levels), site["defaultInterfaceLocale"], copy))}</span><a href="{esc(url)}"><span data-i18n="meta.read">{esc(copy['meta.read'])}</span> →</a></footer></div></article>'''


def build_home(issue: dict[str, Any], index: dict[str, Any], site: dict[str, Any], levels: list[dict[str, Any]], locales: dict[str, dict[str, str]]) -> str:
    copy = locales[site["defaultInterfaceLocale"]]
    level_id = issue_level(issue, site)
    minutes = issue_minutes(issue, level_id, levels)
    first = issue["stories"][0]
    cards = "".join(story_card(story, i, issue, site, levels, copy) for i, story in enumerate(issue["stories"]))
    image = ""
    if first.get("image"):
        image = f'''<figure class="hero-image"><img src="{esc(first["image"]["url"])}" alt="{esc(image_alt(first["image"], site["defaultInterfaceLocale"]))}" referrerpolicy="no-referrer"><figcaption>{esc(first["image"]["credit"])} · <a href="{esc(first["image"]["sourceUrl"])}" rel="noopener noreferrer" target="_blank" data-i18n="article.imageSource">{esc(copy['article.imageSource'])}</a> · <a href="{esc(first["image"]["rightsUrl"])}" rel="noopener noreferrer" target="_blank" data-i18n="article.imageRights">{esc(copy['article.imageRights'])}</a></figcaption></figure>'''
    old = "".join(
        f'<a class="past-issue" href="{esc(site_url(item["date"] + "/", site["basePath"]))}"><time data-date="{esc(item["date"])}">{esc(format_date(item["date"], site["defaultInterfaceLocale"]))}</time><b>{item["storyCount"]} <span data-i18n="meta.materials">{esc(copy["meta.materials"])}</span></b></a>'
        for item in index["dates"][1:4]
    ) or f'<a class="past-issue" href="{esc(site_url("archive/", site["basePath"]))}" data-i18n="archive.open">{esc(copy["archive.open"])}</a>'
    body = f'''
<section class="page home-page">
  <div class="home-kicker"><span data-i18n="home.dailyIssue">{esc(copy['home.dailyIssue'])}</span><time data-date="{esc(issue['date'])}">{esc(format_date(issue['date'], site['defaultInterfaceLocale']))}</time></div>
  <section class="home-hero{' has-image' if image else ''}"><div class="hero-copy"><p class="overline"><span data-date="{esc(issue['date'])}">{esc(format_date(issue['date'], site['defaultInterfaceLocale']))}</span> · {len(issue['stories'])} <span data-i18n="meta.materials">{esc(copy['meta.materials'])}</span> · <span data-i18n="meta.about">{esc(copy['meta.about'])}</span> <span data-issue-minutes>{minutes}</span> <span data-minutes-word>{esc(copy['meta.minutesMany'])}</span></p><h1><span data-i18n="home.heroTitle">{esc(copy['home.heroTitle'])}</span></h1><p class="hero-summary" data-i18n="home.heroSummary">{esc(copy['home.heroSummary'])}</p><div class="hero-actions"><a class="primary-action" href="{esc(site_url(issue['date'] + '/', site['basePath']))}" data-i18n="home.startIssue">{esc(copy['home.startIssue'])}</a>{level_controls(issue, levels, 'article.level')}</div></div>{image}</section>
  <section class="story-section"><header class="section-heading"><div><span data-i18n="home.inIssue">{esc(copy['home.inIssue'])}</span><h2 data-i18n="home.storiesForTime">{esc(copy['home.storiesForTime'])}</h2></div><a href="{esc(site_url(issue['date'] + '/', site['basePath']))}" data-i18n="home.allStories">{esc(copy['home.allStories'])}</a></header><div class="story-list">{cards}</div></section>
  <section class="home-bottom"><div><span class="small-label" data-i18n="home.previousIssues">{esc(copy['home.previousIssues'])}</span>{old}</div><a class="archive-link" href="{esc(site_url('archive/', site['basePath']))}" data-i18n="nav.archive">{esc(copy['nav.archive'])}</a></section>
</section>'''
    return shell(title=format_date(issue["date"], site["defaultInterfaceLocale"]), body=body, page="home", site=site, levels=levels, locales=locales, payload={"issue": issue})


def build_day(issue: dict[str, Any], site: dict[str, Any], levels: list[dict[str, Any]], locales: dict[str, dict[str, str]]) -> str:
    copy = locales[site["defaultInterfaceLocale"]]
    minutes = issue_minutes(issue, issue_level(issue, site), levels)
    cards = "".join(story_card(story, i, issue, site, levels, copy, i == 0) for i, story in enumerate(issue["stories"]))
    body = f'''<section class="page day-page"><header class="day-heading"><a href="{esc(site_url('archive/', site['basePath']))}">← <span data-i18n="nav.archive">{esc(copy['nav.archive'])}</span></a><div><p class="overline" data-i18n="day.issue">{esc(copy['day.issue'])}</p><h1 data-date="{esc(issue['date'])}">{esc(format_date(issue['date'], site['defaultInterfaceLocale']))}</h1><p>{len(issue['stories'])} <span data-i18n="meta.materials">{esc(copy['meta.materials'])}</span> · <span data-i18n="meta.about">{esc(copy['meta.about'])}</span> <span data-issue-minutes>{minutes}</span> <span data-minutes-word>{esc(copy['meta.minutesMany'])}</span></p></div>{level_controls(issue, levels, 'day.readingLevel')}</header><div class="day-grid">{cards}</div></section>'''
    return shell(title=format_date(issue["date"], site["defaultInterfaceLocale"]), body=body, page="day", site=site, levels=levels, locales=locales, payload={"issue": issue})


def build_archive(index: dict[str, Any], issues: dict[str, dict[str, Any]], site: dict[str, Any], levels: list[dict[str, Any]], locales: dict[str, dict[str, str]]) -> str:
    copy = locales[site["defaultInterfaceLocale"]]
    cards = []
    for position, item in enumerate(index["dates"]):
        counts = Counter(story["type"] for story in issues[item["date"]]["stories"])
        tags = "".join(f'<span data-type-count="{kind}" data-count="{counts[kind]}">{counts[kind]} {copy["type." + kind]}</span>' for kind in ("current", "everyday", "history") if counts[kind])
        cards.append(f'''<article class="issue-card{' current-issue' if position == 0 else ''}"><time datetime="{esc(item['date'])}" data-date="{esc(item['date'])}">{esc(format_date(item['date'], site['defaultInterfaceLocale']))}</time><div><p>{item['storyCount']} <span data-i18n="meta.materials">{esc(copy['meta.materials'])}</span> · <span data-i18n="meta.about">{esc(copy['meta.about'])}</span> {item['readingMinutes']} <span data-minutes-word data-minutes="{item['readingMinutes']}">{esc(copy['meta.minutesMany'])}</span></p><div class="issue-tags">{tags}</div></div><a href="{esc(site_url(item['date'] + '/', site['basePath']))}" data-i18n="archive.open">{esc(copy['archive.open'])}</a></article>''')
    body = f'''<section class="page archive-page"><header class="page-title"><p class="overline" data-i18n="nav.archive">{esc(copy['nav.archive'])}</p><h1 data-i18n="archive.title">{esc(copy['archive.title'])}</h1><p data-i18n="archive.summary">{esc(copy['archive.summary'])}</p></header><div class="archive-list">{''.join(cards)}</div></section>'''
    return shell(title=copy["archive.title"], body=body, page="archive", site=site, levels=levels, locales=locales)


def build_article(issue: dict[str, Any], position: int, site: dict[str, Any], levels: list[dict[str, Any]], locales: dict[str, dict[str, str]]) -> str:
    copy = locales[site["defaultInterfaceLocale"]]
    story = issue["stories"][position]
    level_id = issue_level(issue, site)
    level = story["levels"][level_id]
    translation_buttons = "".join(f'<button type="button" data-translation="{esc(code)}">{esc(code.upper())}</button>' for code in issue["translationLocales"])
    paragraphs = "".join(f'<p>{render_units(paragraph, True)}</p>' for paragraph in level["paragraphs"])
    image = ""
    if story.get("image"):
        img = story["image"]
        image = f'''<figure class="article-image"><img src="{esc(img['url'])}" alt="{esc(image_alt(img, site['defaultInterfaceLocale']))}" referrerpolicy="no-referrer"><figcaption>{esc(img['credit'])} · <a href="{esc(img['sourceUrl'])}" rel="noopener noreferrer" target="_blank" data-i18n="article.imageSource">{esc(copy['article.imageSource'])}</a> · <a href="{esc(img['rightsUrl'])}" rel="noopener noreferrer" target="_blank" data-i18n="article.imageRights">{esc(copy['article.imageRights'])}</a></figcaption></figure>'''
    sources = ""
    if story["sources"]:
        links = "".join(f'<a href="{esc(source["url"])}" rel="noopener noreferrer" target="_blank"><b>{esc(source["publisher"])}</b><span>{esc(source["title"])} ↗</span></a>' for source in story["sources"])
        sources = f'<section class="source-box"><span class="small-label" data-i18n="article.sources">{esc(copy["article.sources"])}</span>{links}</section>'
    nav = []
    for target, key, arrow in ((position - 1, "article.previous", "←"), (position + 1, "article.next", "→")):
        if 0 <= target < len(issue["stories"]):
            other = issue["stories"][target]
            other_title = units_text(other["levels"][level_id]["title"])
            nav.append(f'<a href="{esc(site_url(issue["date"] + "/" + other["slug"] + "/", site["basePath"]))}" data-story-target="{target}"><span>{arrow} <i data-i18n="{key}">{esc(copy[key])}</i></span><b dir="rtl">{esc(other_title)}</b></a>')
        else:
            nav.append('<span></span>')
    level = next(item for item in levels if item["id"] == level_id)
    body = f'''<article class="page article-page"><div class="article-progress"><span style="width:{round((position + 1) / len(issue['stories']) * 100)}%"></span></div><header class="article-topline"><a href="{esc(site_url(issue['date'] + '/', site['basePath']))}">← <span data-i18n="nav.backToIssue">{esc(copy['nav.backToIssue'])}</span></a><span>{position + 1} <span data-i18n="article.of">{esc(copy['article.of'])}</span> {len(issue['stories'])}</span></header><div class="article-layout"><aside class="article-tools">{level_controls(issue, levels, 'article.level')}<div class="translation-control"><span data-i18n="article.translation">{esc(copy['article.translation'])}</span><div>{translation_buttons}</div></div><p data-i18n="article.translationHelp">{esc(copy['article.translationHelp'])}</p></aside><div class="article-main"><header class="article-heading"><span class="story-kind" data-story-kind>{esc(story_kind(story, copy))}</span><h1 dir="rtl" data-article-title>{render_units(story['levels'][level_id]['title'], True)}</h1><p class="article-dek" dir="rtl" data-article-teaser>{render_units(story['levels'][level_id]['teaser'], True)}</p><div class="article-meta"><span data-date="{esc(issue['date'])}">{esc(format_date(issue['date'], site['defaultInterfaceLocale']))}</span><span data-article-minutes>{minutes_label(story_minutes(story, level_id, levels), site['defaultInterfaceLocale'], copy)}</span><span data-article-level>{esc(level['label'])} · {esc(level['approximateCefr'])}</span></div></header>{image}<div class="hebrew-article" dir="rtl" data-article-body>{paragraphs}</div>{sources}<nav class="article-pagination">{''.join(nav)}</nav></div></div></article>'''
    return shell(title=units_text(story["levels"][level_id]["title"]), body=body, page="article", site=site, levels=levels, locales=locales, payload={"issue": issue, "storyIndex": position})


def build(root: Path = ROOT, output: Path | None = None, base_path: str | None = None) -> Path:
    errors = validate_repository(root)
    if errors:
        raise RuntimeError("Content validation failed:\n- " + "\n- ".join(errors))
    site = load_site_config(root)
    if base_path is not None:
        site = {**site, "basePath": ensure_base_path(base_path)}
    levels = load_level_config(root)
    locales = load_locales(root)
    index = read_json(root / "content" / "index.json")
    issues = {item["date"]: read_json(root / "content" / f"{item['date']}.json") for item in index["dates"]}
    output = output or root / "dist"
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    shutil.copytree(root / "static", output / "assets")
    latest = issues[index["dates"][0]["date"]]
    (output / "index.html").write_text(build_home(latest, index, site, levels, locales), encoding="utf-8")
    (output / "archive").mkdir()
    (output / "archive" / "index.html").write_text(build_archive(index, issues, site, levels, locales), encoding="utf-8")
    for issue in issues.values():
        day_dir = output / issue["date"]
        day_dir.mkdir()
        (day_dir / "index.html").write_text(build_day(issue, site, levels, locales), encoding="utf-8")
        for position, story in enumerate(issue["stories"]):
            article_dir = day_dir / story["slug"]
            article_dir.mkdir()
            (article_dir / "index.html").write_text(build_article(issue, position, site, levels, locales), encoding="utf-8")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the static magazine.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--base-path", help="Override the configured URL base, for example / for local preview.")
    args = parser.parse_args()
    output = build(args.root.resolve(), args.output.resolve() if args.output else None, args.base_path)
    print(f"Built site at {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
