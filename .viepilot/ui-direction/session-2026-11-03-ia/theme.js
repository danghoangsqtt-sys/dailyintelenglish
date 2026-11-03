// prototype only: compare three colour directions on every page (remembered per browser)
(function () {
  const names = { light: "Sáng", dark: "Tối", cream: "Kem" };
  let pick = "light";
  try { pick = localStorage.getItem("proto-theme") || "light"; } catch (e) {}
  const apply = (t) => { document.documentElement.dataset.theme = t; try { localStorage.setItem("proto-theme", t); } catch (e) {} };
  apply(pick);
  addEventListener("DOMContentLoaded", () => {
    const box = document.createElement("div");
    box.className = "themes";
    box.innerHTML = "<span>Kiểu màu</span>" + Object.entries(names).map(([k, v]) => `<button data-t="${k}">${v}</button>`).join("");
    const mark = () => box.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", b.dataset.t === document.documentElement.dataset.theme));
    box.addEventListener("click", (e) => { const t = e.target.dataset.t; if (t) { apply(t); mark(); } });
    document.body.append(box); mark();
  });
})();
