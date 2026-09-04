(() => {
  "use strict";
  const runtimeNode = document.getElementById("dhr-data");
  if (!runtimeNode) return;
  const runtime = JSON.parse(runtimeNode.textContent);
  const {site, levels, locales, payload, page} = runtime;
  const keys = {interface: "dhr.interfaceLocale", translation: "dhr.translationLocale", level: "dhr.readingLevel"};
  const allowed = (values, saved, fallback) => values.includes(saved) ? saved : (values.includes(fallback) ? fallback : values[0]);
  let interfaceLocale = allowed(site.interfaceLocales, localStorage.getItem(keys.interface), site.defaultInterfaceLocale);
  const issue = payload.issue;
  const availableTranslations = issue ? issue.translationLocales : site.translationLocales;
  let translationLocale = allowed(availableTranslations, localStorage.getItem(keys.translation), site.defaultTranslationLocale);
  const availableLevels = issue ? issue.availableLevels : levels.map(level => level.id);
  let readingLevel = allowed(availableLevels, localStorage.getItem(keys.level), site.defaultReadingLevel);

  const copy = key => (locales[interfaceLocale] || {})[key] || key;
  const unitsNeedSpace = (previous, current) => {
    const previousText = String(previous?.text || "");
    const currentText = String(current?.text || "");
    if (!previousText || !currentText || /\s$/u.test(previousText) || /^\s/u.test(currentText)) return false;
    const noSpacePunctuation = "-־–—/";
    const closingPunctuation = ".,!?;:%…)]}׳״'\"";
    const openingPunctuation = "([{׳״'\"";
    if (closingPunctuation.includes(currentText[0]) || noSpacePunctuation.includes(currentText[0])) return false;
    if (openingPunctuation.includes(previousText.at(-1)) || noSpacePunctuation.includes(previousText.at(-1))) return false;
    if (current.type === "separator") return /^\p{L}+$/u.test(currentText);
    if (previous.type === "separator" && /^\p{L}+$/u.test(previousText)) return false;
    return true;
  };
  const textFor = units => units.reduce((text, unit, index) => text + (index && unitsNeedSpace(units[index - 1], unit) ? " " : "") + unit.text, "");
  const levelInfo = id => levels.find(level => level.id === id) || levels[0];
  const wordCount = level => level.paragraphs.reduce((total, paragraph) => total + paragraph.reduce((sum, unit) => sum + (unit.type === "separator" ? 0 : Math.max(1, unit.text.trim().split(/\s+/).length)), 0), 0);
  const storyMinutes = story => Math.max(1, Math.ceil(wordCount(story.levels[readingLevel]) / levelInfo(readingLevel).learnerWordsPerMinute));
  const issueMinutes = () => issue.stories.reduce((sum, story) => sum + storyMinutes(story), 0);
  const minuteWord = count => {
    const category = new Intl.PluralRules(interfaceLocale).select(count);
    const key = category === "one" ? "meta.minute" : category === "few" ? "meta.minutesFew" : "meta.minutesMany";
    return locales[interfaceLocale][key] || locales[interfaceLocale]["meta.minutesMany"];
  };
  const formatDate = value => new Intl.DateTimeFormat(interfaceLocale, {day:"numeric", month:"long", year:"numeric", timeZone:"UTC"}).format(new Date(`${value}T00:00:00Z`));
  const kind = story => {
    const label = `${copy(`category.${story.category}`)} · ${copy(`type.${story.type}`)}`;
    return story.type === "everyday" ? `${label} · ${copy("type.aiGenerated")}` : label;
  };

  function activateControls() {
    document.querySelectorAll("[data-level]").forEach(button => {
      button.classList.toggle("active", button.dataset.level === readingLevel);
      button.setAttribute("aria-pressed", String(button.dataset.level === readingLevel));
    });
    document.querySelectorAll("[data-translation]").forEach(button => {
      button.classList.toggle("active", button.dataset.translation === translationLocale);
      button.setAttribute("aria-pressed", String(button.dataset.translation === translationLocale));
    });
  }

  function renderUnit(unit) {
    if (unit.type === "separator") return document.createTextNode(unit.text);
    const translation = unit.translations?.[translationLocale];
    if (typeof translation !== "string" || !translation.trim()) return document.createTextNode(unit.text);
    const button = document.createElement("button");
    button.type = "button";
    button.className = "lexeme";
    button.textContent = unit.text;
    button.dataset.unitType = unit.type;
    button.dataset.translations = JSON.stringify(unit.translations);
    return button;
  }

  function renderUnits(units) {
    const nodes = [];
    units.forEach((unit, index) => {
      if (index && unitsNeedSpace(units[index - 1], unit)) nodes.push(document.createTextNode(" "));
      nodes.push(renderUnit(unit));
    });
    return nodes;
  }

  function renderArticle() {
    if (page !== "article" || !issue) return;
    const story = issue.stories[payload.storyIndex];
    const content = story.levels[readingLevel];
    document.querySelector("[data-article-title]").replaceChildren(...renderUnits(content.title));
    document.querySelector("[data-article-teaser]").replaceChildren(...renderUnits(content.teaser));
    const articleBody = document.querySelector("[data-article-body]");
    articleBody.replaceChildren(...content.paragraphs.map(units => {
      const paragraph = document.createElement("p");
      paragraph.append(...renderUnits(units));
      return paragraph;
    }));
    document.querySelector("[data-article-minutes]").textContent = `${storyMinutes(story)} ${minuteWord(storyMinutes(story))}`;
    const info = levelInfo(readingLevel);
    document.querySelector("[data-article-level]").textContent = `${info.label} · ${info.approximateCefr}`;
    document.querySelectorAll(".article-pagination a").forEach(link => {
      const target = Number(link.dataset.storyTarget);
      if (issue.stories[target]) link.querySelector("b").textContent = textFor(issue.stories[target].levels[readingLevel].title);
    });
  }

  function renderCards() {
    if (!issue) return;
    document.querySelectorAll("[data-story-index]").forEach(card => {
      const story = issue.stories[Number(card.dataset.storyIndex)];
      const content = story.levels[readingLevel];
      card.querySelector("[data-story-title]").textContent = textFor(content.title);
      card.querySelector("[data-story-teaser]").textContent = textFor(content.teaser);
      card.querySelector("[data-story-minutes]").textContent = `${storyMinutes(story)} ${minuteWord(storyMinutes(story))}`;
      card.querySelector("[data-story-kind]").textContent = kind(story);
      const image = card.querySelector("img");
      if (image && story.image) image.alt = story.image.alt[interfaceLocale] || Object.values(story.image.alt)[0];
    });
    document.querySelectorAll("[data-issue-minutes]").forEach(node => node.textContent = issueMinutes());
  }

  function renderLocale() {
    document.documentElement.lang = interfaceLocale;
    document.querySelectorAll("[data-i18n]").forEach(node => node.textContent = copy(node.dataset.i18n));
    document.querySelector(".site-nav")?.setAttribute("aria-label", copy("accessibility.primaryNavigation"));
    document.querySelectorAll("[data-date]").forEach(node => node.textContent = formatDate(node.dataset.date));
    document.querySelectorAll("[data-type-count]").forEach(node => node.textContent = `${node.dataset.count} ${copy(`type.${node.dataset.typeCount}`)}`);
    document.querySelectorAll("[data-minutes-word]").forEach(node => {
      const sibling = node.previousElementSibling;
      const count = node.dataset.minutes ? Number(node.dataset.minutes) : (sibling && Number(sibling.textContent));
      node.textContent = minuteWord(Number.isFinite(count) ? count : 2);
    });
    const select = document.getElementById("interface-locale");
    if (select) select.value = interfaceLocale;
    if (issue && page === "article") {
      const story = issue.stories[payload.storyIndex];
      document.querySelector("[data-story-kind]").textContent = kind(story);
      const img = document.querySelector(".article-image img");
      if (img && story.image) img.alt = story.image.alt[interfaceLocale] || Object.values(story.image.alt)[0];
    }
    const heroImage = document.querySelector(".hero-image img");
    if (heroImage && issue?.stories[0]?.image) heroImage.alt = issue.stories[0].image.alt[interfaceLocale] || Object.values(issue.stories[0].image.alt)[0];
    renderCards();
    renderArticle();
  }

  function closePopover() {
    document.querySelectorAll(".word-popover").forEach(node => node.remove());
    document.querySelectorAll(".lexeme.active").forEach(node => node.classList.remove("active"));
  }

  function openPopover(button) {
    closePopover();
    const translations = JSON.parse(button.dataset.translations);
    const popup = document.createElement("span");
    popup.className = "word-popover";
    popup.setAttribute("role", "tooltip");
    const original = document.createElement("b"); original.textContent = button.childNodes[0].textContent;
    const translation = document.createElement("span"); translation.textContent = translations[translationLocale] || "—";
    const type = document.createElement("small"); type.textContent = `${button.dataset.unitType} · ${translationLocale.toUpperCase()}`;
    popup.append(original, translation, type);
    button.append(popup);
    button.classList.add("active");
  }

  document.addEventListener("click", event => {
    const levelButton = event.target.closest("[data-level]");
    if (levelButton) {
      readingLevel = levelButton.dataset.level;
      localStorage.setItem(keys.level, readingLevel);
      closePopover(); activateControls(); renderCards(); renderArticle();
      return;
    }
    const translationButton = event.target.closest("[data-translation]");
    if (translationButton) {
      translationLocale = translationButton.dataset.translation;
      localStorage.setItem(keys.translation, translationLocale);
      closePopover(); activateControls(); renderArticle();
      return;
    }
    const lexeme = event.target.closest(".lexeme");
    if (lexeme) {
      event.stopPropagation();
      lexeme.classList.contains("active") ? closePopover() : openPopover(lexeme);
    } else closePopover();
  });
  document.addEventListener("mouseover", event => {
    const lexeme = event.target.closest(".lexeme");
    if (lexeme && !lexeme.contains(event.relatedTarget) && window.matchMedia("(hover:hover)").matches) openPopover(lexeme);
  });
  document.addEventListener("mouseout", event => {
    const lexeme = event.target.closest(".lexeme");
    if (lexeme && !lexeme.contains(event.relatedTarget) && window.matchMedia("(hover:hover)").matches) closePopover();
  });
  document.addEventListener("focusin", event => {
    if (event.target.matches(".lexeme")) openPopover(event.target);
  });
  document.addEventListener("keydown", event => { if (event.key === "Escape") closePopover(); });
  document.getElementById("interface-locale")?.addEventListener("change", event => {
    interfaceLocale = allowed(site.interfaceLocales, event.target.value, site.defaultInterfaceLocale);
    localStorage.setItem(keys.interface, interfaceLocale);
    closePopover(); renderLocale();
  });
  document.querySelectorAll("figure img").forEach(img => {
    const removeBrokenImage = () => {
      img.closest(".has-image")?.classList.remove("has-image");
      img.closest("figure")?.remove();
    };
    img.addEventListener("error", removeBrokenImage);
    if (img.complete && img.naturalWidth === 0) removeBrokenImage();
  });

  activateControls();
  renderLocale();
})();
