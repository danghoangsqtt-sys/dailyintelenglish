// Prototype only: draws the rail (or the phone tab bar), and inside one video the title, the 3 stages with their 7 steps,
// and the Back / Next bar. <body data-page="home|create|channel|videos|library" data-step="1..7">
(function () {
  const ICON = "../../session-2026-11-03-ia/icons.svg";
  const I = (id, cls = "") => `<svg class="i ${cls}" aria-hidden="true"><use href="${ICON}#${id}"/></svg>`;
  const b = document.body, page = b.dataset.page, step = Number(b.dataset.step || 0);
  const items = [["home", "home.html", "home", "Hôm nay", 3], ["channel", "channel.html", "calendar", "Kênh"],
                 ["videos", "videos.html", "film", "Video"], ["library", "library.html", "library", "Thư viện"]];
  const rail = document.createElement("nav");
  rail.className = "rail"; rail.setAttribute("aria-label", "Điều hướng chính");
  rail.innerHTML = `<a class="brand" href="home.html"><img src="../../../../frontend/static/brand/logo-64.png" alt="">Daily Beyond English</a>
    <a class="btn primary" href="create.html"${page === "create" ? ' aria-current="page"' : ""}>${I("plus")}Tạo video</a>
    ${items.map(([k, href, ic, t, n]) => `<a class="nav" href="${href}"${k === page ? ' aria-current="page"' : ""}>${I(ic)}${t}${n ? `<span class="count num">${n}</span>` : ""}</a>`).join("")}
    <a class="nav bottom" href="#">${I("settings")}Cài đặt</a>`;
  b.prepend(rail);
  if (!step) return;

  const main = document.querySelector("main");
  const S = [["Nội dung", [[1, "Thiết lập"], [2, "Kịch bản"], [3, "Học liệu"]]], ["Sản xuất", [[4, "Giọng đọc"], [5, "Video"]]], ["Đăng", [[6, "Ảnh bìa"], [7, "YouTube"]]]];
  const bar = document.createElement("header");
  bar.className = "flowbar";
  bar.innerHTML = `<div class="t"><a class="btn ghost sm" href="videos.html">${I("back")}Video</a><h1>Câu bị động: hiểu bản chất</h1>
      <span class="cefr">B1</span><span class="saved">${I("check", "sm")}Đã lưu</span></div>
    <nav class="stages" aria-label="Các bước">${S.map(([name, xs]) => `<div class="stage"><span>${name}</span>${xs.map(([n, t]) =>
      `<a class="stp${n < step ? " done" : ""}" href="step-${n}.html"${n === step ? ' aria-current="step"' : ""}><i>${n < step ? "✓" : n}</i>${t}</a>`).join("")}</div>`).join("")}</nav>`;
  main.prepend(bar);
  const next = ["", "Viết kịch bản", "Tạo học liệu", "Sang giọng đọc", "Sang dựng video", "Sang ảnh bìa", "Sang YouTube", "Duyệt và lên lịch"][step];
  const foot = document.createElement("div");
  foot.className = "flowfoot";
  foot.innerHTML = `${step > 1 ? `<a class="btn" href="step-${step - 1}.html" aria-label="Bước trước">${I("back")}<span class="lbl">Bước trước</span></a>` : `<a class="btn" href="create.html" aria-label="Đổi mẫu">${I("back")}<span class="lbl">Đổi mẫu</span></a>`}
    <span class="grow"></span><a class="btn primary" href="${step < 7 ? `step-${step + 1}.html` : "home.html"}">${next}${I("arrow")}</a>`;
  main.append(foot);
})();
