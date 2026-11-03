// Prototype only: the shared sidebar, top bar, the stage bar inside one video, and the mascot (Lina) in the corner.
// <body data-page="home|create|channel|videos|library" data-crumbs="A|B" data-step="1..7"
//       data-say="what the mascot says on this page" data-acts="Label=href|Label=href" data-pose="gesture-…">
(function () {
  const I = (id, cls = "") => `<svg class="i ${cls}"><use href="../icons.svg#${id}"/></svg>`;
  const R = "../../../../";
  const b = document.body, page = b.dataset.page, step = Number(b.dataset.step || 0);
  const nav = [
    ["home", "home.html", "home", "Hôm nay", 3],
    ["channel", "channel.html", "calendar", "Kênh"],
    ["videos", "videos.html", "film", "Video của tôi"],
    ["library", "library.html", "library", "Thư viện"],
  ].map(([k, href, ic, t, n]) => `<a href="${href}"${k === page ? ' aria-current="page"' : ""}>${I(ic)}${t}${n ? `<span class="n">${n}</span>` : ""}</a>`).join("");
  // v5: the sidebar keeps only places; series, automation and notifications were repeats of Kênh and Hôm nay
  const side = `<aside class="side">
    <a class="ws" href="home.html"><img src="${R}frontend/static/brand/logo-64.png" alt=""><span class="grow"><b>Daily Beyond English</b></span></a>
    <a class="btn primary new" href="create.html"${page === "create" ? ' aria-current="page"' : ""}>${I("plus")}Tạo video</a>
    <nav class="nav">${nav}</nav>
    <div class="foot"><nav class="nav"><a href="#">${I("help")}Hướng dẫn</a><a href="#">${I("settings")}Cài đặt</a></nav></div></aside>`;
  const crumbs = (b.dataset.crumbs || "").split("|").filter(Boolean)
    .map((c, i, a) => (i === a.length - 1 ? `<b>${c}</b>` : `<a href="${c === "Video của tôi" ? "videos.html" : "#"}">${c}</a>${I("chev")}`)).join("");
  const top = `<header class="topbar"><div class="crumbs">${crumbs}</div>
    <div class="search">${I("search", "sm")}Tìm video, mẫu, nhân vật…<kbd>Ctrl K</kbd></div></header>`;

  let flow = "", foot = "";
  if (step) {
    const S = [["Nội dung", [[1, "Thiết lập", "flow-1-setup.html"], [2, "Kịch bản", "flow-2-script.html"], [3, "Học liệu", "flow-3-learning.html"]]],
               ["Sản xuất", [[4, "Giọng đọc", "flow-4-voice.html"], [5, "Video", "flow-5-video.html"]]],
               ["Đăng", [[6, "Ảnh bìa", "flow-6-thumbnail.html"], [7, "YouTube", "flow-7-youtube.html"]]]];
    const steps = S.map(([name, xs]) => `<div class="stage"><em>${name}</em>${xs.map(([n, t, href]) =>
      `<a class="stp${n < step ? " done" : ""}" href="${href}"${n === step ? ' aria-current="step"' : ""}><i>${n < step ? "✓" : n}</i>${t}</a>`).join("")}</div>`).join("");
    flow = `<div class="flowbar"><div class="in">
      <div class="title"><div class="grow"><div class="row" style="gap:8px"><h1>Câu bị động: hiểu bản chất</h1><span class="badge plain">Ngữ pháp · Short</span>
        <span class="saved">${I("check", "sm")}Đã lưu</span></div></div>
        <a class="btn ghost" href="#">${I("eye")}Xem trước</a></div>
      <nav class="steps">${steps}</nav></div></div>`;
    const prev = ["", "", "flow-1-setup.html", "flow-2-script.html", "flow-3-learning.html", "flow-4-voice.html", "flow-5-video.html", "flow-6-thumbnail.html"][step];
    const nextName = ["", "Viết kịch bản", "Tạo học liệu", "Sang giọng đọc", "Sang dựng video", "Sang ảnh bìa", "Sang YouTube", "Duyệt và lên lịch"][step];
    const nextHref = ["", "flow-2-script.html", "flow-3-learning.html", "flow-4-voice.html", "flow-5-video.html", "flow-6-thumbnail.html", "flow-7-youtube.html", "home.html"][step];
    foot = `<div class="flowfoot"><div class="in">
      ${prev ? `<a class="btn ghost" href="${prev}">${I("back")}Bước trước</a>` : `<a class="btn ghost" href="create.html">${I("back")}Đổi mẫu</a>`}
      <span class="grow"></span><a class="btn primary" href="${nextHref}">${nextName}${I("arrow")}</a></div></div>`;
    b.classList.add("has-flowfoot");
  }
  const main = document.querySelector("main");
  const shell = document.createElement("div");
  shell.className = "shell";
  shell.innerHTML = side + `<div class="content">${top}${flow}</div>`;
  b.prepend(shell);
  shell.querySelector(".content").append(main);
  if (foot) shell.querySelector(".content").insertAdjacentHTML("beforeend", foot);

  // ---- the mascot: Lina as a half-body VTuber. Frames come from her talking sprites (mascot/build_lina.py):
  // a front set and a three-quarter "side" set in the same outfit. Mouth and blink swap frames at once; poses and turns cross-fade.
  const say = b.dataset.say;
  if (!say) return;
  const acts = (b.dataset.acts || "").split("|").filter(Boolean).map((x, i) => {
    const [label, href] = x.split("=");
    return `<a class="btn sm${i ? "" : " primary"}" href="${href || "#"}">${label}</a>`;
  }).join("");
  const DIR = "../mascot/lina/";
  let mini = false;
  try { mini = sessionStorage.getItem("mascot-mini") === "1"; } catch (e) {}
  const m = document.createElement("div");
  m.className = "mascot" + (mini ? " mini" : "");
  m.innerHTML = `<div class="bubble" role="status"><div class="who">Lina<span class="x">
      <a data-act="voice" title="Đọc to">${I("mic", "sm")}</a><a data-act="mini" title="Thu nhỏ">${I("chevd", "sm")}</a></span></div>
      <div class="said"></div>${acts ? `<div class="acts" hidden>${acts}</div>` : ""}</div>
    <div class="body" title="Bấm để nghe lại"><div class="rig"><div class="breath"><img class="front" alt="Lina"><img class="back" alt=""></div></div></div>
    <div class="mini-face" title="Mở trợ lý"><img src="${DIR}front/calm__closed.webp" alt="Lina"><b></b></div>`;
  document.body.append(m);
  const said = m.querySelector(".said"), actBox = m.querySelector(".acts"), bubble = m.querySelector(".bubble");
  let shown = m.querySelector("img.front"), under = m.querySelector("img.back");

  const st = { view: "front", pose: "calm", open: false, blink: false, talking: false };
  const isGesture = (p) => p.startsWith("gesture-");
  function frameName() {
    const { view, pose, open, blink } = st;
    if (blink && pose === "calm") return "blink";
    if (isGesture(pose)) return pose + (open ? "__open" : "");
    return view === "front" ? (open ? "calm__open" : "calm__closed") : `${pose}__${open ? "open" : "closed"}`;
  }
  const cache = {};
  const url = (view, name) => `${DIR}${view}/${name}.webp`;
  ["front", "side"].forEach((v) => ["calm__closed", "calm__open", "blink"].forEach((n) => { (cache[url(v, n)] = new Image()).src = url(v, n); }));
  function preload(view, pose) {
    const names = isGesture(pose) ? [pose, pose + "__open"] : view === "front" ? [] : [`${pose}__closed`, `${pose}__open`];
    return Promise.all(names.map((n) => { const u = url(view, n); if (!cache[u]) { cache[u] = new Image(); cache[u].src = u; }
      return cache[u].decode().catch(() => {}); }));
  }
  function draw(fade) {
    const u = url(st.view, frameName());
    if (!fade) { shown.src = u; return; }
    under.src = u;
    under.classList.remove("back"); shown.classList.add("back");
    [shown, under] = [under, shown];
  }
  async function set(change, fade = true) {
    Object.assign(st, change);
    if (change.view || change.pose) await preload(st.view, st.pose);
    if (change.view && fade) { m.classList.add("turning"); setTimeout(() => m.classList.remove("turning"), 340); }
    draw(fade);
  }
  set({}, false);

  // blinking: only on the calm face, every 2.5–6 s, a double blink now and then
  (function blinkLoop() {
    setTimeout(() => {
      if (st.pose === "calm" && !st.talking) {
        st.blink = true; draw(false);
        setTimeout(() => { st.blink = false; draw(false);
          if (Math.random() < .2) setTimeout(() => { st.blink = true; draw(false); setTimeout(() => { st.blink = false; draw(false); }, 110); }, 160);
        }, 120);
      }
      blinkLoop();
    }, 2500 + Math.random() * 3500);
  })();

  // idle life: now and then she looks at the page (three-quarter view, toward the content) or back at you, or smiles
  (function idleLoop() {
    setTimeout(async () => {
      if (!st.talking && !m.classList.contains("mini")) {
        const r = Math.random();
        if (st.view === "front") await set({ view: "side", pose: r < .3 ? "smile" : "calm" });
        else if (r < .55) await set({ view: "front", pose: "calm" });
        else await set({ pose: r < .75 ? "smile" : r < .9 ? "gesture-listen" : "calm" });
      }
      idleLoop();
    }, 6000 + Math.random() * 6000);
  })();

  // talking: face you, take the page's gesture, flap the mouth with the words (open on vowels, shut between words)
  let flapTimer = 0, hideTimer = 0;
  function flap(on) {
    clearInterval(flapTimer);
    if (!on) { st.open = false; draw(false); return; }
    let beat = 0;
    flapTimer = setInterval(() => { beat++; st.open = beat % 3 !== 0 && Math.random() > .15; draw(false); }, 95);
  }
  function speak(text) {
    if (!("speechSynthesis" in window)) return false;
    const voice = speechSynthesis.getVoices().find((v) => v.lang && v.lang.toLowerCase().startsWith("vi"));
    if (!voice) return false;
    const u = new SpeechSynthesisUtterance(text);
    u.voice = voice; u.lang = voice.lang; u.rate = 1.02;
    u.onend = u.onerror = () => done();
    speechSynthesis.cancel(); speechSynthesis.speak(u);
    return true;
  }
  let speaking = false;
  function done() {
    speaking = false; st.talking = false; flap(false); m.classList.remove("talking");
    setTimeout(() => { if (!st.talking) set({ pose: "calm" }); }, 900);
    clearTimeout(hideTimer);
    hideTimer = setTimeout(() => { if (!st.talking) bubble.classList.add("gone"); }, 9000);  // the bubble steps aside when unused
  }
  async function talk(withVoice) {
    clearTimeout(hideTimer); bubble.classList.remove("gone");
    said.textContent = ""; if (actBox) actBox.hidden = true;
    st.talking = true; m.classList.add("talking");
    await set({ view: "front", pose: b.dataset.pose || "gesture-talk" });
    flap(true);
    const words = say.split(" ");
    let i = 0;
    const caret = document.createElement("span"); caret.className = "caret";
    speaking = withVoice && speak(say);
    const tick = () => {
      said.textContent = words.slice(0, ++i).join(" "); said.append(caret);
      if (i < words.length) setTimeout(tick, 85 + words[i - 1].length * 18);
      else { caret.remove(); if (actBox) actBox.hidden = false; if (!speaking) done(); }
    };
    tick();
  }
  m.addEventListener("click", (e) => {
    const a = e.target.closest("[data-act]");
    if (a && a.dataset.act === "mini") { m.classList.add("mini"); try { sessionStorage.setItem("mascot-mini", "1"); } catch (x) {} if ("speechSynthesis" in window) speechSynthesis.cancel(); return; }
    if (a && a.dataset.act === "voice") { talk(true); return; }
    if (e.target.closest(".mini-face")) { m.classList.remove("mini"); try { sessionStorage.setItem("mascot-mini", "0"); } catch (x) {} talk(false); return; }
    if (e.target.closest(".body")) talk(true);
  });
  if (!mini) setTimeout(() => talk(false), 600);
})();
