const params = new URLSearchParams(window.location.search);
const validThemes = ["editorial", "clear", "cafe", "grid"];
const validPages = ["home", "archive", "day", "article"];
const validDevices = ["desktop", "mobile"];

let theme = validThemes.includes(params.get("theme")) ? params.get("theme") : "editorial";
let page = validPages.includes(params.get("page")) ? params.get("page") : "home";
let device = validDevices.includes(params.get("device")) ? params.get("device") : "desktop";

function render() {
  document.body.dataset.theme = theme;
  document.querySelector(".preview-stage").dataset.device = device;
  document.querySelectorAll(".mock-page").forEach((node) => {
    node.hidden = node.dataset.page !== page;
  });
  document.querySelectorAll("[data-theme-choice]").forEach((button) => {
    button.classList.toggle("active", button.dataset.themeChoice === theme);
  });
  document.querySelectorAll("[data-page-choice]").forEach((button) => {
    button.classList.toggle("active", button.dataset.pageChoice === page);
  });
  document.querySelectorAll("[data-device-choice]").forEach((button) => {
    button.classList.toggle("active", button.dataset.deviceChoice === device);
  });
  const next = new URLSearchParams({theme, page, device});
  history.replaceState(null, "", `${window.location.pathname}?${next}`);
  window.scrollTo({top: 0, behavior: "instant"});
}

document.querySelectorAll("[data-theme-choice]").forEach((button) => button.addEventListener("click", () => {
  theme = button.dataset.themeChoice;
  render();
}));
document.querySelectorAll("[data-page-choice]").forEach((button) => button.addEventListener("click", () => {
  page = button.dataset.pageChoice;
  render();
}));
document.querySelectorAll("[data-device-choice]").forEach((button) => button.addEventListener("click", () => {
  device = button.dataset.deviceChoice;
  render();
}));
document.querySelectorAll("[data-open-page]").forEach((link) => link.addEventListener("click", (event) => {
  event.preventDefault();
  page = link.dataset.openPage;
  render();
}));

render();
