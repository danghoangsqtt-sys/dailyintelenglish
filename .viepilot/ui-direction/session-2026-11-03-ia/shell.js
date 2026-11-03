// Prototype only: the shared sidebar, top bar and (for one video) the stage bar, so every page has the same frame.
// <body data-page="home|create|channel|videos|library" data-crumbs="A|B" data-step="1..7">
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
  const side = `<aside class="side">
    <a class="ws" href="home.html"><img src="${R}frontend/static/brand/logo-64.png" alt=""><span class="grow"><b>Daily Beyond English</b><small>Kênh YouTube · 12,4 N</small></span>${I("chevd", "sm")}</a>
    <a class="btn primary new" href="create.html">${I("plus")}Tạo video</a>
    <nav class="nav">${nav}</nav>
    <div class="label">Series đang chạy</div>
    <nav class="nav">
      <a href="channel.html"><span style="width:8px;height:8px;border-radius:2px;background:#17803d;margin:0 5px"></span>Ngữ pháp bản chất</a>
      <a href="channel.html"><span style="width:8px;height:8px;border-radius:2px;background:#0f766e;margin:0 5px"></span>Một gốc – cả họ từ</a>
      <a href="channel.html"><span style="width:8px;height:8px;border-radius:2px;background:#d97706;margin:0 5px"></span>The Office Startup</a>
    </nav>
    <div class="foot">
      <div class="usage"><div class="row" style="gap:6px">${I("moon", "sm")}<b style="font-weight:600">Tự động đêm nay 23:00</b></div><div class="muted" style="margin-top:2px">2 video · máy rảnh 6 giờ</div></div>
      <nav class="nav"><a href="#">${I("help")}Hướng dẫn</a><a href="#">${I("settings")}Cài đặt</a></nav>
    </div></aside>`;
  const crumbs = (b.dataset.crumbs || "").split("|").filter(Boolean)
    .map((c, i, a) => (i === a.length - 1 ? `<b>${c}</b>` : `<span>${c}</span>${I("chev")}`)).join("");
  const top = `<header class="topbar"><div class="crumbs">${crumbs}</div>
    <div class="search">${I("search", "sm")}Tìm video, mẫu, nhân vật…<kbd>Ctrl K</kbd></div>
    <a class="iconbtn" href="#" title="Thông báo">${I("bell")}<span class="dot"></span></a>
    <img class="avatar" src="${R}frontend/static/brand/logo-64.png" alt=""></header>`;

  let flow = "", foot = "";
  if (step) {
    const S = [["Nội dung", [[1, "Thiết lập", "flow-1-setup.html"], [2, "Kịch bản", "flow-2-script.html"], [3, "Học liệu", "flow-3-learning.html"]]],
               ["Sản xuất", [[4, "Giọng đọc", "flow-4-voice.html"], [5, "Video", "flow-5-video.html"]]],
               ["Đăng", [[6, "Ảnh bìa", "flow-6-thumbnail.html"], [7, "YouTube", "flow-7-youtube.html"]]]];
    const steps = S.map(([name, xs]) => `<div class="stage"><em>${name}</em>${xs.map(([n, t, href]) =>
      `<a class="stp${n < step ? " done" : ""}" href="${href}"${n === step ? ' aria-current="step"' : ""}><i>${n < step ? "✓" : n}</i>${t}</a>`).join("")}</div>`).join("");
    flow = `<div class="flowbar"><div class="in">
      <div class="title"><div class="thumb"><img src="${R}frontend/static/samples/grammar-vi.jpg" alt=""></div>
        <div class="grow"><div class="row" style="gap:8px"><h1>Câu bị động: hiểu bản chất</h1><span class="badge plain">Ngữ pháp · Short 9:16</span></div>
        <div class="saved">${I("check", "sm")}Đã lưu tự động · Series Ngữ pháp bản chất · Tập 1</div></div>
        <a class="btn ghost" href="#">${I("eye")}Xem trước</a><a class="btn" href="#">${I("more")}</a></div>
      <nav class="steps">${steps}</nav></div></div>`;
    const prev = [0, "", "flow-1-setup.html", "flow-2-script.html", "flow-3-learning.html", "flow-4-voice.html", "flow-5-video.html", "flow-6-thumbnail.html"][step];
    const nextName = ["", "Viết kịch bản", "Tạo học liệu", "Sang giọng đọc", "Sang dựng video", "Sang ảnh bìa", "Sang YouTube", "Duyệt và lên lịch"][step];
    const nextHref = ["", "flow-2-script.html", "flow-3-learning.html", "flow-4-voice.html", "flow-5-video.html", "flow-6-thumbnail.html", "flow-7-youtube.html", "home.html"][step];
    foot = `<div class="flowfoot"><div class="in">
      ${prev ? `<a class="btn ghost" href="${prev}">${I("back")}Bước trước</a>` : `<a class="btn ghost" href="create.html">${I("back")}Đổi mẫu</a>`}
      <span class="hint grow" style="text-align:center">${b.dataset.hint || ""}</span>
      <a class="btn primary" href="${nextHref}">${nextName}${I("arrow")}</a></div></div>`;
  }
  const main = document.querySelector("main");
  const shell = document.createElement("div");
  shell.className = "shell";
  shell.innerHTML = side + `<div class="content">${top}${flow}</div>`;
  b.prepend(shell);
  shell.querySelector(".content").append(main);
  if (foot) shell.querySelector(".content").insertAdjacentHTML("beforeend", foot);
})();
