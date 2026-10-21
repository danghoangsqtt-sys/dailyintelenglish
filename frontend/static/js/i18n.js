/**
 * Phase 58 (ENH-040): the interface language -- English (the source text of every page) or Tiếng Việt.
 *
 * The pages stay written in English. In Vietnamese mode this layer replaces, as the page is built and whenever it
 * changes, every interface text whose trimmed English wording is in the dictionary (`I18N_VI.text`, then the regex
 * `I18N_VI.patterns` for texts with numbers), in text nodes and in the placeholder / title / aria-label attributes.
 * Anything inside `[translate="no"]` (scripts, names, titles, voices, the owner's own text) and form values are
 * never touched. English mode does nothing at all. The choice is kept per computer in localStorage (`dbe.lang`).
 */
(() => {
  const KEY = "dbe.lang";
  const ATTRIBUTES = ["placeholder", "title", "aria-label"];
  const SKIP = new Set(["SCRIPT", "STYLE", "TEXTAREA", "CODE", "PRE"]);
  const originals = new WeakMap();  // text node -> English text, so switching back restores it
  let lang = "en";
  try { lang = localStorage.getItem(KEY) === "vi" ? "vi" : "en"; } catch { /* English */ }
  let observer = null;
  let pending = new Set();
  let scheduled = false;

  const dictionary = () => window.I18N_VI || { text: {}, patterns: [] };

  /** The Vietnamese for one English interface text, or null when there is none. */
  function translate(english) {
    const key = english.replace(/\s+/g, " ").trim();
    if (!key) return null;
    const { text, patterns } = dictionary();
    if (Object.prototype.hasOwnProperty.call(text, key)) return text[key];
    // patterns are anchored regexes; the replacement may use $1… or be a function of the match
    for (const [pattern, replacement] of patterns) {
      if (pattern.test(key)) return key.replace(pattern, replacement);
    }
    return null;
  }

  function excluded(element) {
    for (let node = element; node && node.nodeType === 1; node = node.parentElement) {
      if (SKIP.has(node.tagName) || node.getAttribute("translate") === "no") return true;
    }
    return false;
  }

  function translateText(node) {
    const english = originals.has(node) ? originals.get(node) : node.nodeValue;
    const vietnamese = translate(english);
    if (vietnamese === null) return;
    if (!originals.has(node)) originals.set(node, english);
    const lead = english.match(/^\s*/)[0];
    const tail = english.match(/\s*$/)[0];
    const value = lead + vietnamese + tail;
    if (node.nodeValue !== value) node.nodeValue = value;
  }

  function translateAttributes(element) {
    for (const name of ATTRIBUTES) {
      if (!element.hasAttribute(name)) continue;
      const stored = `data-i18n-${name}`;
      const english = element.getAttribute(stored) ?? element.getAttribute(name);
      const vietnamese = translate(english);
      if (vietnamese === null) continue;
      if (!element.hasAttribute(stored)) element.setAttribute(stored, english);
      if (element.getAttribute(name) !== vietnamese) element.setAttribute(name, vietnamese);
    }
  }

  function walk(root) {
    if (!root) return;
    if (root.nodeType === 3) {
      if (root.parentElement && !excluded(root.parentElement)) translateText(root);
      return;
    }
    if (root.nodeType !== 1 && root.nodeType !== 9) return;
    if (root.nodeType === 1 && excluded(root)) return;
    if (root.nodeType === 1) translateAttributes(root);
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        if (node.nodeType === 1 && (SKIP.has(node.tagName) || node.getAttribute("translate") === "no")) {
          return NodeFilter.FILTER_REJECT;
        }
        return NodeFilter.FILTER_ACCEPT;
      },
    });
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      if (node.nodeType === 3) translateText(node);
      else translateAttributes(node);
    }
  }

  function flush() {
    scheduled = false;
    const roots = [...pending];
    pending = new Set();
    roots.forEach(walk);
    translateTitle();
  }

  function schedule(node) {
    pending.add(node);
    if (!scheduled) {
      scheduled = true;
      requestAnimationFrame(flush);
    }
  }

  let englishTitle = null;
  function translateTitle() {
    const title = document.title;
    if (englishTitle !== null && title === translatedTitle(englishTitle)) return;
    englishTitle = title;
    const [page, ...rest] = title.split(" — ");
    const vietnamese = translate(page);
    if (vietnamese !== null) document.title = [vietnamese, ...rest].join(" — ");
  }
  function translatedTitle(title) {
    const [page, ...rest] = title.split(" — ");
    const vietnamese = translate(page);
    return vietnamese === null ? title : [vietnamese, ...rest].join(" — ");
  }

  function start() {
    document.documentElement.lang = "vi";
    walk(document.documentElement);
    translateTitle();
    observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        if (mutation.type === "childList") mutation.addedNodes.forEach(schedule);
        else if (mutation.type === "characterData") {
          // a script rewrote the text: forget the old English so the new one is translated
          originals.delete(mutation.target);
          schedule(mutation.target);
        } else if (mutation.type === "attributes") {
          const element = mutation.target;
          const name = mutation.attributeName;
          const value = element.getAttribute(name);
          if (value !== null && value !== translate(element.getAttribute(`data-i18n-${name}`) || "")) {
            element.removeAttribute(`data-i18n-${name}`);
          }
          schedule(element);
        }
      }
    });
    observer.observe(document.documentElement, {
      childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ATTRIBUTES,
    });
  }

  function addSwitch() {
    const theme = document.getElementById("theme-toggle");
    if (!theme || document.getElementById("lang-switch")) return;
    const box = document.createElement("div");
    box.id = "lang-switch";
    box.className = "lang-switch";
    box.setAttribute("role", "group");
    box.setAttribute("aria-label", "Interface language");
    box.setAttribute("translate", "no");
    [["en", "EN", "English"], ["vi", "VI", "Tiếng Việt"]].forEach(([code, label, name]) => {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = label;
      button.title = name;
      button.dataset.lang = code;
      button.setAttribute("aria-pressed", String(code === lang));
      button.addEventListener("click", () => set(code));
      box.append(button);
    });
    theme.parentNode.insertBefore(box, theme);
  }

  /** Switch the interface language; English reloads the page so every text is its original again. */
  function set(next) {
    next = next === "vi" ? "vi" : "en";
    if (next === lang) return;
    try { localStorage.setItem(KEY, next); } catch { /* the choice lasts only for this page */ }
    if (next === "en") {
      location.reload();
      return;
    }
    lang = next;
    document.querySelectorAll("#lang-switch button").forEach((button) => {
      button.setAttribute("aria-pressed", String(button.dataset.lang === lang));
    });
    start();
    document.dispatchEvent(new CustomEvent("i18n:change", { detail: { lang } }));
  }

  window.I18n = Object.freeze({ lang: () => lang, set, translate: (english) => (lang === "vi" ? translate(english) ?? english : english) });

  if (lang === "vi") start();
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", addSwitch);
  else addSwitch();
})();
