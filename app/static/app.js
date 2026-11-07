"use strict";

const $ = (selector) => document.querySelector(selector);
const statusNames = {open: "Открыто", in_progress: "В работе", done: "Завершено"};
const priorityNames = {low: "Низкий", medium: "Средний", high: "Высокий"};
let session = null;
let projects = [];
let selectedProject = null;
let editedIssue = null;
let registerMode = false;
let listVersion = 0;
let noticeTimer;
let searchTimer;

function node(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text; // Never interpret user content as HTML.
  return element;
}

function announce(message) {
  $("#notice").textContent = message;
  $("#notice").hidden = false;
  clearTimeout(noticeTimer);
  noticeTimer = setTimeout(() => { $("#notice").hidden = true; }, 4500);
}

function showAuth() {
  session = null;
  selectedProject = null;
  listVersion++;
  document.querySelectorAll("dialog[open]").forEach((dialog) => dialog.close());
  $("#auth-view").hidden = false;
  $("#board-view").hidden = true;
}

async function api(path, options = {}) {
  const headers = {"Content-Type": "application/json"};
  if (session) headers["X-CSRF-Token"] = session.csrf_token;
  let response;
  try {
    response = await fetch(path, {
      ...options, credentials: "same-origin", headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
    });
  } catch {
    throw new Error("Нет связи с сервером. Проверьте соединение и повторите.");
  }
  if (response.status === 204) return null;
  let data;
  try { data = await response.json(); }
  catch { throw new Error("Ошибка сервера. Повторите действие позже."); }
  if (!response.ok) {
    if (response.status === 401 && session) {
      showAuth();
      $("#auth-error").textContent = "Сессия завершилась. Войдите снова.";
    }
    const names = {username: "Имя пользователя", password: "Пароль", name: "Название",
      title: "Название", description: "Описание", status: "Статус", priority: "Приоритет"};
    const fields = (data.errors || []).map((error) => names[error.field] || error.field);
    throw new Error((data.detail || "Ошибка запроса. Повторите позже.") + (fields.length ? " Поля: " + fields.join(", ") + "." : ""));
  }
  return data;
}

async function submit(form, errorElement, action) {
  const button = form.querySelector('[type="submit"]');
  errorElement.textContent = "";
  button.disabled = true;
  try { await action(); }
  catch (error) { errorElement.textContent = error.message; }
  finally { button.disabled = false; }
}

$("#auth-switch").addEventListener("click", () => {
  registerMode = !registerMode;
  $("#auth-heading").textContent = registerMode ? "Создать аккаунт" : "Войти в IssueBoard";
  $("#auth-caption").textContent = registerMode ? "Начало работы" : "С возвращением";
  $("#auth-description").textContent = registerMode ? "Ваши проекты будут доступны только вам." : "Продолжите работу над своими проектами.";
  $("#auth-submit").textContent = registerMode ? "Зарегистрироваться" : "Войти";
  $("#auth-switch").textContent = registerMode ? "Войти" : "Зарегистрироваться";
  $("#auth-switch-copy").textContent = registerMode ? "Уже есть аккаунт?" : "Ещё нет аккаунта?";
  $("#password").autocomplete = registerMode ? "new-password" : "current-password";
  $("#auth-error").textContent = "";
});

$("#auth-form").addEventListener("submit", (event) => {
  event.preventDefault();
  submit(event.target, $("#auth-error"), async () => {
    const body = Object.fromEntries(new FormData(event.target));
    if (registerMode) {
      await api("/api/auth/register", {method: "POST", body});
      $("#auth-switch").click();
      announce("Аккаунт создан. Теперь войдите.");
      $("#password").value = "";
      $("#password").focus();
      return;
    }
    session = await api("/api/auth/login", {method: "POST", body});
    $("#password").value = "";
    await loadWorkspace();
  });
});

$("#logout").addEventListener("click", async () => {
  try {
    await api("/api/auth/logout", {method: "POST"});
    showAuth();
    location.hash = "";
    announce("Вы вышли из аккаунта.");
  } catch (error) { announce(error.message); }
});

function resetFilters() {
  $("#filters").reset();
}

function renderProjects() {
  $("#projects").replaceChildren();
  $("#projects-empty").hidden = projects.length > 0;
  for (const project of projects) {
    const link = node("a", "project-link", project.name);
    link.href = "#project-" + project.id;
    if (project.id === selectedProject?.id) link.setAttribute("aria-current", "page");
    $("#projects").append(link);
  }
}

async function loadWorkspace() {
  $("#auth-view").hidden = true;
  $("#board-view").hidden = false;
  projects = await api("/api/projects");
  $("#current-user").textContent = session.username;
  await selectProjectFromHash();
}

async function selectProjectFromHash() {
  if (!session) return;
  const match = location.hash.match(/^#project-(\d+)$/);
  selectedProject = projects.find((project) => project.id === Number(match?.[1])) || projects[0] || null;
  listVersion++;
  renderProjects();
  $("#workspace-error").textContent = "";
  $("#welcome").hidden = !!selectedProject;
  $("#project-view").hidden = !selectedProject;
  if (!selectedProject) return;
  $("#project-name").textContent = selectedProject.name;
  $("#project-description").textContent = selectedProject.description;
  document.title = selectedProject.name + " — IssueBoard";
  resetFilters();
  try { await refreshIssues(); }
  catch (error) { $("#workspace-error").textContent = error.message; }
}

window.addEventListener("hashchange", selectProjectFromHash);

function openProjectDialog() {
  $("#project-form").reset();
  $("#project-error").textContent = "";
  $("#project-dialog").showModal();
}
$("#add-project").addEventListener("click", openProjectDialog);
$("#first-project").addEventListener("click", openProjectDialog);
document.querySelectorAll(".close-dialog").forEach((button) =>
  button.addEventListener("click", () => button.closest("dialog").close()));

$("#project-form").addEventListener("submit", (event) => {
  event.preventDefault();
  submit(event.target, $("#project-error"), async () => {
    const project = await api("/api/projects", {method: "POST", body: Object.fromEntries(new FormData(event.target))});
    projects.unshift(project);
    $("#project-dialog").close();
    if (location.hash === "#project-" + project.id) await selectProjectFromHash();
    else location.hash = "#project-" + project.id;
    announce("Проект создан.");
  });
});

async function refreshIssues() {
  if (!selectedProject) return;
  const projectId = selectedProject.id;
  const version = ++listVersion;
  const params = new URLSearchParams({q: $("#search").value, sort: $("#sort").value});
  if ($("#filter-status").value) params.set("status", $("#filter-status").value);
  if ($("#filter-priority").value) params.set("priority", $("#filter-priority").value);
  const [issues, metrics] = await Promise.all([
    api("/api/projects/" + projectId + "/issues?" + params),
    api("/api/projects/" + projectId + "/metrics"),
  ]);
  if (version !== listVersion || projectId !== selectedProject?.id) return;
  $("#workspace-error").textContent = "";
  for (const [key, value] of Object.entries(metrics)) $("#metric-" + key).textContent = value;
  $("#results-count").textContent = "Найдено: " + issues.length;
  $("#issues-list").replaceChildren();
  for (const issue of issues) {
    const row = node("article", "issue-row");
    const main = node("div", "issue-main");
    const title = node("button", "issue-title", issue.title);
    title.type = "button";
    title.addEventListener("click", () => openIssue(issue));
    main.append(title, node("div", "issue-meta", "#" + issue.id + " / " + issue.type.toUpperCase()));
    row.append(main, node("span", "badge status-" + issue.status, statusNames[issue.status]),
      node("span", "badge priority-" + issue.priority, priorityNames[issue.priority]),
      node("time", "issue-date", formatDate(issue.updated_at)));
    row.querySelector("time").dateTime = issue.updated_at;
    $("#issues-list").append(row);
  }
  const filtered = $("#search").value || $("#filter-status").value || $("#filter-priority").value;
  $("#issues-empty").hidden = issues.length > 0;
  $("#empty-heading").textContent = filtered ? "Ничего не найдено" : "Пока нет issues";
  $("#empty-description").textContent = filtered ? "Попробуйте другой запрос или сбросьте фильтры." : "Добавьте первую ошибку или задачу.";
  $("#empty-action").textContent = filtered ? "Сбросить фильтры" : "Создать issue";
}

function formatDate(value) {
  return new Intl.DateTimeFormat("ru-RU", {day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit"}).format(new Date(value));
}

async function refreshSafely() {
  try { await refreshIssues(); }
  catch (error) { $("#workspace-error").textContent = error.message; }
}

$("#filters").addEventListener("submit", (event) => { event.preventDefault(); refreshSafely(); });
$("#search").addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(refreshSafely, 250);
});
["#filter-status", "#filter-priority", "#sort"].forEach((selector) =>
  $(selector).addEventListener("change", refreshSafely));
$("#empty-action").addEventListener("click", () => {
  if ($("#search").value || $("#filter-status").value || $("#filter-priority").value) {
    resetFilters(); refreshSafely();
  } else openIssue();
});

async function openIssue(issue = null) {
  editedIssue = issue;
  $("#issue-form").reset();
  $("#issue-error").textContent = "";
  $("#issue-dialog-title").textContent = issue ? "Issue #" + issue.id : "Новый issue";
  $("#delete-issue").hidden = !issue;
  $("#history-section").hidden = !issue;
  $("#history").replaceChildren();
  if (issue) {
    for (const key of ["title", "description", "type", "priority", "status"]) $("#issue-" + key).value = issue[key];
  }
  $("#issue-dialog").showModal();
  if (issue) {
    const projectId = selectedProject.id;
    try {
      const history = await api("/api/projects/" + projectId + "/issues/" + issue.id + "/history");
      if (editedIssue?.id !== issue.id || selectedProject?.id !== projectId) return;
      for (const item of history) {
        const change = (item.old_status ? statusNames[item.old_status] : "Создано") + " → " + statusNames[item.new_status];
        $("#history").append(node("li", "", change + " · " + item.actor + " · " + formatDate(item.changed_at)));
      }
    } catch (error) { $("#issue-error").textContent = error.message; }
  }
}

$("#add-issue").addEventListener("click", () => openIssue());
$("#issue-form").addEventListener("submit", (event) => {
  event.preventDefault();
  submit(event.target, $("#issue-error"), async () => {
    const root = "/api/projects/" + selectedProject.id + "/issues";
    await api(editedIssue ? root + "/" + editedIssue.id : root, {
      method: editedIssue ? "PUT" : "POST", body: Object.fromEntries(new FormData(event.target)),
    });
    $("#issue-dialog").close();
    announce(editedIssue ? "Issue обновлён." : "Issue создан.");
    await refreshSafely();
  });
});

$("#delete-issue").addEventListener("click", async () => {
  if (!editedIssue || !confirm('Удалить issue «' + editedIssue.title + '» и его историю? Это действие нельзя отменить.')) return;
  const button = $("#delete-issue");
  button.disabled = true;
  try {
    await api("/api/projects/" + selectedProject.id + "/issues/" + editedIssue.id, {method: "DELETE"});
    $("#issue-dialog").close();
    announce("Issue удалён.");
    await refreshSafely();
  } catch (error) { $("#issue-error").textContent = error.message; }
  finally { button.disabled = false; }
});

(async function start() {
  try {
    session = await api("/api/auth/session");
    await loadWorkspace();
  } catch (error) {
    if (session) $("#workspace-error").textContent = error.message;
    else if (!error.message.includes("Войдите")) $("#auth-error").textContent = error.message;
  }
})();