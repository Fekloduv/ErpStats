const state = {
  sprintCount: 9,
  sprintDaysCalendar: 30,
  sprintDaysWork: 20,
  catalog: [],
  metricsCatalog: [],
  config: {},
  actuals: {},
  totalWeights: 0,
};

const tableHead = document.querySelector("#metricsTable thead");
const tableBody = document.querySelector("#metricsTable tbody");
const editTargetsBtn = document.getElementById("editTargetsBtn");
const editMetricTargetsBtn = document.getElementById("editMetricTargetsBtn");
const reportBtn = document.getElementById("reportBtn");
const planBtn = document.getElementById("planBtn");
const reportPanel = document.getElementById("reportPanel");
const periodSelect = document.getElementById("periodSelect");
const refreshReportBtn = document.getElementById("refreshReportBtn");
const laggingSummary = document.getElementById("laggingSummary");
const laggingCriticalList = document.getElementById("laggingCriticalList");
const laggingExecutorList = document.getElementById("laggingExecutorList");
const laggingCustomerList = document.getElementById("laggingCustomerList");
const laggingDependenciesList = document.getElementById("laggingDependenciesList");
const debtsList = document.getElementById("debtsList");
const forecastText = document.getElementById("forecastText");
const recommendationsList = document.getElementById("recommendationsList");
const progressValue = document.getElementById("progressValue");
const progressDetail = document.getElementById("progressDetail");
const progressBarFill = document.getElementById("progressBarFill");
const reportDetailsHead = document.querySelector("#reportDetailsTable thead");
const reportDetailsBody = document.querySelector("#reportDetailsTable tbody");
const weightsSummary = document.getElementById("weightsSummary");
const timelineWrap = document.getElementById("timelineWrap");

const targetsDialog = document.getElementById("targetsDialog");
const targetsForm = document.getElementById("targetsForm");
const targetsGrid = document.getElementById("targetsGrid");
const cancelTargetsBtn = document.getElementById("cancelTargetsBtn");

const metricTargetsDialog = document.getElementById("metricTargetsDialog");
const metricTargetsForm = document.getElementById("metricTargetsForm");
const metricTargetsGrid = document.getElementById("metricTargetsGrid");
const cancelMetricTargetsBtn = document.getElementById("cancelMetricTargetsBtn");

const actualsDialog = document.getElementById("actualsDialog");
const actualsForm = document.getElementById("actualsForm");
const actualsTitle = document.getElementById("actualsTitle");
const actualsFields = document.getElementById("actualsFields");
const cancelActualsBtn = document.getElementById("cancelActualsBtn");
const planDialog = document.getElementById("planDialog");
const planForm = document.getElementById("planForm");
const planTableBody = document.getElementById("planTableBody");
const planTimelineWrap = document.getElementById("planTimelineWrap");
const closePlanBtn = document.getElementById("closePlanBtn");

let activeSprint = null;

async function api(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Ошибка запроса");
  }
  return data;
}

function numberFormat(value) {
  return Number(value || 0).toLocaleString("ru-RU", { maximumFractionDigits: 2 });
}

function getMetricName(metricId) {
  const metric = state.metricsCatalog.find((item) => item.id === Number(metricId));
  return metric?.name || `Метрика ${metricId}`;
}

function getTaskProgress(sprintKey, task) {
  const metricId = String(task.metricId);
  const target = Number(task.target || 0);
  const actual = Number((state.actuals[sprintKey]?.metricActuals || {})[metricId] || 0);
  const progress = target > 0 ? Math.min((actual / target) * 100, 100) : 0;
  return { target, actual, progress };
}

function getCustomerProgress(sprintKey) {
  const tasks = state.config[sprintKey]?.tasks || [];
  if (!tasks.length) return 0;
  const values = tasks.map((task) => getTaskProgress(sprintKey, task).progress);
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function renderLaggingItems(items) {
  laggingCriticalList.innerHTML = "";
  laggingExecutorList.innerHTML = "";
  laggingCustomerList.innerHTML = "";
  laggingDependenciesList.innerHTML = "";

  if (items.length === 0) {
    laggingSummary.textContent = "Нарушений сроков и критических отставаний нет.";
    laggingCriticalList.innerHTML = "<li>Нет критичных отклонений.</li>";
    laggingExecutorList.innerHTML = "<li>Отставаний не выявлено.</li>";
    laggingCustomerList.innerHTML = "<li>Отставаний не выявлено.</li>";
    laggingDependenciesList.innerHTML = "<li>Блокирующих зависимостей нет.</li>";
    return;
  }

  const critical = items
    .filter((item) => Number(item.severity || 0) >= 60)
    .sort((a, b) => Number(b.severity || 0) - Number(a.severity || 0));
  const executor = items.filter((item) => item.area === "Исполнитель");
  const customer = items.filter((item) => item.area === "Заказчик");
  const dependencies = items.filter((item) => item.area === "Зависимости");

  laggingSummary.textContent = `Всего отклонений: ${items.length}. Критичных: ${critical.length}.`;

  const fillList = (target, list, emptyText) => {
    if (list.length === 0) {
      target.innerHTML = `<li>${emptyText}</li>`;
      return;
    }
    list.forEach((item) => {
      const li = document.createElement("li");
      li.textContent = `Спринт ${item.sprint}: ${item.problem}`;
      target.appendChild(li);
    });
  };

  fillList(laggingCriticalList, critical, "Нет критичных отклонений.");
  fillList(laggingExecutorList, executor, "Нарушений у Исполнителя нет.");
  fillList(laggingCustomerList, customer, "Нарушений у Заказчика нет.");
  fillList(laggingDependenciesList, dependencies, "Блокирующих зависимостей нет.");
}

function renderTable() {
  tableHead.innerHTML = "";
  tableBody.innerHTML = "";

  const headRow = document.createElement("tr");
  headRow.innerHTML = `
    <th>Спринт</th>
    <th>Работы Исполнителя / Заказчика</th>
    <th>План (вес и метрика)</th>
    <th>Факт</th>
    <th>Статус</th>
    <th>Действия</th>
  `;
  tableHead.appendChild(headRow);

  for (let sprint = 1; sprint <= state.sprintCount; sprint += 1) {
    const sprintKey = String(sprint);
    const sprintItem = state.catalog.find((item) => item.id === sprint);
    const cfg = state.config[sprintKey] || {};
    const act = state.actuals[sprintKey] || {};
    const tasks = cfg.tasks || [];
    const executorProgress = Number(act.executorProgress || 0);
    const customerProgress = getCustomerProgress(sprintKey);

    const maxScore = Number(cfg.executorWeight || 0) + Number(cfg.customerWeight || 0);
    const earnedScore =
      (Number(cfg.executorWeight || 0) * executorProgress) / 100 +
      (Number(cfg.customerWeight || 0) * customerProgress) / 100;
    const sprintPercent = maxScore > 0 ? (earnedScore / maxScore) * 100 : 0;

    let statusClass = "badge-warn";
    if (sprintPercent >= 95) {
      statusClass = "badge-ok";
    } else if (sprintPercent >= 60) {
      statusClass = "badge-mid";
    }

    const tasksText = tasks.length
      ? tasks
          .map((task) => {
            const p = getTaskProgress(sprintKey, task);
            return `${getMetricName(task.metricId)} (${task.months} мес.): ${numberFormat(p.actual)} / ${numberFormat(p.target)}`;
          })
          .join("<br>")
      : "Метрики не выбраны";

    const row = document.createElement("tr");
    row.innerHTML = `
      <td>Спринт ${sprint}</td>
      <td>
        <div><strong>${sprintItem?.title || ""}</strong></div>
        <small>Исполнитель: ${sprintItem?.executorWork || ""}</small><br>
        <small>Заказчик: ${sprintItem?.customerWork || ""}</small><br>
        <small>Зависимости: ${(sprintItem?.dependencies || []).length ? sprintItem.dependencies.join(", ") : "нет"}</small>
      </td>
      <td>
        <div>Вес И/З: <strong>${numberFormat(cfg.executorWeight)} / ${numberFormat(cfg.customerWeight)}</strong></div>
        <div>Выбранные метрики:</div>
        <small>${tasksText}</small>
      </td>
      <td>
        <div>Исполнитель: <strong>${numberFormat(executorProgress)}%</strong></div>
        <div>Заказчик (авто по метрике): <strong>${numberFormat(customerProgress)}%</strong></div>
      </td>
      <td><strong class="${statusClass}">${numberFormat(sprintPercent)}%</strong><br><small>${numberFormat(earnedScore)} / ${numberFormat(maxScore)} баллов</small></td>
      <td><button class="btn btn-secondary" data-sprint="${sprint}">Внести данные</button></td>
    `;
    tableBody.appendChild(row);
  }

  weightsSummary.textContent = `Сумма весов по всем спринтам: ${numberFormat(state.totalWeights)} баллов (должно быть ровно 100).`;
}

function renderPeriodOptions() {
  const prevValue = periodSelect.value;
  periodSelect.innerHTML = "";
  for (let i = 1; i <= state.sprintCount; i += 1) {
    const option = document.createElement("option");
    option.value = String(i);
    option.textContent = `${i} спринт(ов)`;
    if (prevValue && Number(prevValue) === i) {
      option.selected = true;
    } else if (!prevValue && i === state.sprintCount) {
      option.selected = true;
    }
    periodSelect.appendChild(option);
  }
}

function openTargetsDialog() {
  targetsGrid.innerHTML = "";
  for (let sprint = 1; sprint <= state.sprintCount; sprint += 1) {
    const sprintKey = String(sprint);
    const sprintItem = state.catalog.find((item) => item.id === sprint);
    const cfg = state.config[sprintKey] || {};
    const row = document.createElement("details");
    row.className = "sprint-accordion";
    const selected = new Map((cfg.tasks || []).map((task) => [String(task.metricId), task]));
    const options = state.metricsCatalog
      .map((metric) => {
        const task = selected.get(String(metric.id));
        return `
          <div class="task-option">
            <div class="task-option-head">
              <input type="checkbox" data-sprint="${sprint}" data-role="task-enabled" data-metric="${metric.id}" ${task ? "checked" : ""}>
              <span>${metric.name}</span>
            </div>
          </div>
        `;
      })
      .join("");

    row.innerHTML = `
      <summary>
        <strong>Спринт ${sprint}: ${sprintItem?.title || ""}</strong>
      </summary>
      <div class="accordion-body">
        <div class="target-metrics target-metrics-weights">
          <label>
            Вес Исполнителя
            <input type="number" min="0" max="100" step="0.01" data-sprint="${sprint}" data-field="executorWeight" value="${cfg.executorWeight ?? 0}">
          </label>
          <label>
            Вес Заказчика
            <input type="number" min="0" max="100" step="0.01" data-sprint="${sprint}" data-field="customerWeight" value="${cfg.customerWeight ?? 0}">
          </label>
        </div>
        <div class="target-metrics">
          ${options}
        </div>
      </div>
    `;
    targetsGrid.appendChild(row);
  }
  targetsDialog.showModal();
}

function openMetricTargetsDialog() {
  metricTargetsGrid.innerHTML = "";
  for (let sprint = 1; sprint <= state.sprintCount; sprint += 1) {
    const sprintKey = String(sprint);
    const sprintItem = state.catalog.find((item) => item.id === sprint);
    const cfg = state.config[sprintKey] || {};
    const tasks = cfg.tasks || [];
    if (!tasks.length) continue;

    const row = document.createElement("details");
    row.className = "sprint-accordion";
    row.innerHTML = `
      <summary>
        <strong>Спринт ${sprint}: ${sprintItem?.title || ""}</strong>
      </summary>
      <div class="accordion-body">
        <div class="target-metrics">
          ${tasks
            .map((task) => {
              const metricId = String(task.metricId);
              return `
                <label>
                  Цель задачи: ${getMetricName(task.metricId)}
                  <input type="number" min="0" step="0.01" data-sprint="${sprint}" data-metric="${metricId}" data-role="target" value="${Number(task.target || 0)}">
                </label>
                <label>
                  Длительность задачи, мес.
                  <input type="number" min="1" max="${state.sprintCount}" step="1" data-sprint="${sprint}" data-metric="${metricId}" data-role="target-months" value="${Number(task.months || 1)}">
                </label>
              `;
            })
            .join("")}
        </div>
      </div>
    `;
    metricTargetsGrid.appendChild(row);
  }
  metricTargetsDialog.showModal();
}

function openActualsDialog(sprint) {
  activeSprint = sprint;
  const sprintKey = String(sprint);
  const sprintItem = state.catalog.find((item) => item.id === sprint);
  const cfg = state.config[sprintKey] || {};
  const act = state.actuals[sprintKey] || {};
  const tasks = cfg.tasks || [];

  actualsTitle.textContent = `Внести данные: спринт ${sprint} (${sprintItem?.title || ""})`;
  const taskFields = tasks
    .map((task) => {
      const metricId = String(task.metricId);
      return `
        <label>
          Фактическое значение: ${getMetricName(task.metricId)} (цель: ${numberFormat(task.target)})
          <input type="number" min="0" step="0.01" name="metricActual_${metricId}" value="${Number((act.metricActuals || {})[metricId] || 0)}">
        </label>
      `;
    })
    .join("");

  actualsFields.innerHTML = `
    <label>
      Исполнитель: выполнение этапов (0-100%)
      <input type="number" min="0" max="100" step="0.01" name="executorProgress" value="${act.executorProgress ?? 0}">
    </label>
    ${taskFields || "<p class='muted'>Метрики для спринта не выбраны. Сначала настройте план.</p>"}
    <label>
      Комментарии / долги
      <textarea name="notes" rows="3">${act.notes ?? ""}</textarea>
    </label>
  `;
  actualsDialog.showModal();
}

async function saveTargets(event) {
  event.preventDefault();
  const inputs = targetsGrid.querySelectorAll("input[data-sprint][data-field]");
  const config = {};
  for (let sprint = 1; sprint <= state.sprintCount; sprint += 1) {
    config[String(sprint)] = {
      executorWeight: 0,
      customerWeight: 0,
      tasks: [],
    };
  }

  inputs.forEach((input) => {
    const sprint = input.dataset.sprint;
    const field = input.dataset.field;
    const value = Number(input.value || 0);
    config[sprint][field] = Math.max(0, Math.min(value, 100));
  });

  const totalWeights = Object.values(config).reduce(
    (sum, sprintConfig) => sum + Number(sprintConfig.executorWeight || 0) + Number(sprintConfig.customerWeight || 0),
    0
  );
  if (Math.abs(totalWeights - 100) > 0.01) {
    alert(`Сумма весов должна быть ровно 100. Сейчас: ${numberFormat(totalWeights)}.`);
    return;
  }

  const checkboxes = targetsGrid.querySelectorAll("input[data-role='task-enabled']");
  checkboxes.forEach((checkbox) => {
    if (!(checkbox instanceof HTMLInputElement) || !checkbox.checked) return;
    const sprint = checkbox.dataset.sprint;
    const metric = String(checkbox.dataset.metric || "0");
    const existingTask = (state.config[sprint]?.tasks || []).find((task) => String(task.metricId) === metric);
    config[sprint].tasks.push({
      metricId: Number(metric),
      months: Number(existingTask?.months || 1),
    });
  });

  try {
    await api("/api/config", {
      method: "POST",
      body: JSON.stringify({ config }),
    });
    targetsDialog.close();
    await loadState();
    if (!reportPanel.hidden) {
      await loadReport();
    }
  } catch (error) {
    alert(error.message);
  }
}

async function saveMetricTargets(event) {
  event.preventDefault();
  const targets = {};
  for (let sprint = 1; sprint <= state.sprintCount; sprint += 1) {
    targets[String(sprint)] = {};
  }
  const inputs = metricTargetsGrid.querySelectorAll("input[data-role='target']");
  inputs.forEach((input) => {
    const sprint = input.dataset.sprint;
    const metric = input.dataset.metric;
    const monthsInput = metricTargetsGrid.querySelector(
      `input[data-role='target-months'][data-sprint='${sprint}'][data-metric='${metric}']`
    );
    targets[sprint][metric] = {
      target: Number(input.value || 0),
      months: Number(monthsInput?.value || 1),
    };
  });

  try {
    await api("/api/targets", {
      method: "POST",
      body: JSON.stringify({ targets }),
    });
    metricTargetsDialog.close();
    await loadState();
    if (!reportPanel.hidden) {
      await loadReport();
    }
  } catch (error) {
    alert(error.message);
  }
}

async function saveActuals(event) {
  event.preventDefault();
  if (!activeSprint) return;

  const formData = new FormData(actualsForm);
  const metricActuals = {};
  const cfgTasks = state.config[String(activeSprint)]?.tasks || [];
  cfgTasks.forEach((task) => {
    const key = `metricActual_${task.metricId}`;
    metricActuals[String(task.metricId)] = Number(formData.get(key) || 0);
  });
  const values = {
    executorProgress: Number(formData.get("executorProgress") || 0),
    metricActuals,
    notes: String(formData.get("notes") || ""),
  };

  try {
    await api(`/api/actuals/${activeSprint}`, {
      method: "POST",
      body: JSON.stringify({ values }),
    });
    actualsDialog.close();
    await loadState();
    if (!reportPanel.hidden) {
      await loadReport();
    }
  } catch (error) {
    alert(error.message);
  }
}

function progressColor(progress) {
  const value = Number(progress || 0);
  if (value >= 95) return "#2f855a";
  if (value >= 60) return "#4c6fb3";
  return "#b7791f";
}

function laneColor(owner, progress) {
  const value = Number(progress || 0);
  if (owner === "executor") {
    if (value >= 95) return "rgba(47, 158, 100, 0.45)";
    if (value >= 60) return "rgba(82, 183, 136, 0.38)";
    return "rgba(116, 198, 157, 0.32)";
  }
  if (value >= 95) return "rgba(61, 109, 204, 0.45)";
  if (value >= 60) return "rgba(94, 129, 216, 0.38)";
  return "rgba(142, 168, 232, 0.32)";
}

function buildPlanRow(sprint) {
  const sprintKey = String(sprint);
  const sprintItem = state.catalog.find((item) => item.id === sprint);
  const cfg = state.config[sprintKey] || {};
  const tasks = cfg.tasks || [];
  const taskPlanText = tasks.length
    ? tasks
        .map((task) => `${getMetricName(task.metricId)} (${task.months} мес.), цель ${numberFormat(task.target)}`)
        .join("<br>")
    : "Метрики не выбраны";

  return `
    <tr>
      <td><strong>Спринт ${sprint}</strong><br><small>${sprintItem?.title || ""}</small></td>
      <td>
        <div>Вес И/З: <strong>${numberFormat(cfg.executorWeight)} / ${numberFormat(cfg.customerWeight)}</strong></div>
        <div><small>${taskPlanText}</small></div>
      </td>
    </tr>
  `;
}

function renderTimeline(targetElement, customerItems, executorItems, options = {}) {
  if (!targetElement) return;
  const showProgress = options.showProgress ?? true;
  const maxCols = state.sprintCount;
  const board = document.createElement("div");
  board.className = "timeline-board";

  const header = document.createElement("div");
  header.className = "timeline-header";
  header.innerHTML = `<div class="timeline-label">Спринт</div>`;
  const headerMonths = document.createElement("div");
  headerMonths.className = "timeline-months";
  headerMonths.style.gridTemplateColumns = `repeat(${maxCols}, minmax(62px, 1fr))`;
  for (let col = 1; col <= maxCols; col += 1) {
    const month = document.createElement("div");
    month.className = "timeline-month";
    month.textContent = `М${col}`;
    headerMonths.appendChild(month);
  }
  header.appendChild(headerMonths);
  board.appendChild(header);

  for (let sprint = 1; sprint <= state.sprintCount; sprint += 1) {
    const lanes = [
      {
        key: "executor",
        title: `Спринт ${sprint}`,
        subtitle: "Исполнитель",
        items: executorItems.filter((item) => Number(item.headSprint) === sprint),
      },
      {
        key: "customer",
        title: `Спринт ${sprint}`,
        subtitle: "Заказчик",
        items: customerItems.filter((item) => Number(item.headSprint) === sprint),
      },
    ];

    lanes.forEach((lane) => {
      const row = document.createElement("div");
      row.className = "timeline-row";
      row.innerHTML = `
        <div class="timeline-label">
          <span>${lane.title}</span>
          <span class="timeline-label-sub">${lane.subtitle}</span>
        </div>
      `;

      const track = document.createElement("div");
      track.className = "timeline-track";
      track.style.gridTemplateColumns = `repeat(${maxCols}, minmax(62px, 1fr))`;

      lane.items.forEach((item) => {
        const start = Math.max(1, Number(item.startSprint || sprint));
        const duration = Math.max(1, Number(item.durationMonths || 1));
        const safeSpan = Math.min(duration, maxCols - start + 1);
        const task = document.createElement("div");
        task.className = `timeline-task ${lane.key === "executor" ? "timeline-task-executor" : "timeline-task-customer"}`;
        task.style.gridColumn = `${start} / span ${safeSpan}`;

        const progressFill = document.createElement("div");
        progressFill.className = "timeline-task-progress";
        if (showProgress) {
          progressFill.style.background = laneColor(lane.key, item.progress);
          progressFill.style.width = `${Math.max(0, Math.min(Number(item.progress || 0), 100))}%`;
        } else {
          progressFill.style.background = "transparent";
          progressFill.style.width = "0%";
        }

        const label = document.createElement("div");
        label.className = "timeline-task-label";
        label.textContent = showProgress ? `${item.metricName} (${numberFormat(item.progress)}%)` : `${item.metricName}`;

        task.appendChild(progressFill);
        task.appendChild(label);
        track.appendChild(task);
      });

      row.appendChild(track);
      board.appendChild(row);
    });
  }

  targetElement.innerHTML = "";
  targetElement.appendChild(board);
}

async function openPlanDialog() {
  try {
    planTableBody.innerHTML = "";
    for (let sprint = 1; sprint <= state.sprintCount; sprint += 1) {
      planTableBody.insertAdjacentHTML("beforeend", buildPlanRow(sprint));
    }
    const reportData = await api("/api/report", {
      method: "POST",
      body: JSON.stringify({ period: state.sprintCount }),
    });
    renderTimeline(
      planTimelineWrap,
      reportData.customerTimeline || reportData.timeline || [],
      reportData.executorTimeline || [],
      { showProgress: false }
    );
    planDialog.showModal();
  } catch (error) {
    alert(error.message);
  }
}

async function loadReport() {
  const period = Number(periodSelect.value || state.sprintCount);
  try {
    const data = await api("/api/report", {
      method: "POST",
      body: JSON.stringify({ period }),
    });

    reportPanel.hidden = false;
    progressValue.textContent = `${data.progressPercent.toFixed(2)}%`;
    progressDetail.textContent = `Показатель внедрения: ${numberFormat(data.scoreActual)} из ${numberFormat(data.scoreMax)} баллов`;
    progressBarFill.style.width = `${Math.min(data.progressPercent, 100)}%`;

    renderLaggingItems(data.delayedItems);

    debtsList.innerHTML = "";
    if (data.debts.length === 0) {
      debtsList.innerHTML = "<li>Накопленных долгов нет.</li>";
    } else {
      data.debts.forEach((item) => {
        const li = document.createElement("li");
        li.textContent = `Спринт ${item.sprint} (${item.title}): дефицит ${numberFormat(item.gapPoints)} баллов`;
        debtsList.appendChild(li);
      });
    }

    forecastText.textContent = data.forecast;

    recommendationsList.innerHTML = "";
    data.recommendations.forEach((text) => {
      const li = document.createElement("li");
      li.textContent = text;
      recommendationsList.appendChild(li);
    });

    reportDetailsHead.innerHTML = `
      <tr>
        <th>Спринт</th>
        <th>Исполнитель %</th>
        <th>Заказчик %</th>
        <th>Метрика план/факт</th>
        <th>Баллы</th>
        <th>Комментарий</th>
      </tr>
    `;
    reportDetailsBody.innerHTML = "";
    data.sprintDetails.forEach((item) => {
      const metricsText = (item.metrics || [])
        .map((metric) => `${metric.metricName}: ${numberFormat(metric.actual)} / ${numberFormat(metric.target)} (${numberFormat(metric.progress)}%)`)
        .join("<br>");
      const row = document.createElement("tr");
      row.innerHTML = `
        <td>${item.sprint}. ${item.title}</td>
        <td>${numberFormat(item.executorStatus)}%</td>
        <td>${numberFormat(item.customerStatus)}%</td>
        <td>${metricsText || "-"}</td>
        <td>${numberFormat(item.sprintScore)} / ${numberFormat(item.sprintMax)}</td>
        <td>${item.notes || "-"}</td>
      `;
      reportDetailsBody.appendChild(row);
    });
    renderTimeline(timelineWrap, data.customerTimeline || data.timeline || [], data.executorTimeline || []);
  } catch (error) {
    alert(error.message);
  }
}

async function loadState() {
  const data = await api("/api/state");
  state.sprintCount = data.sprintCount;
  state.sprintDaysCalendar = data.sprintDaysCalendar;
  state.sprintDaysWork = data.sprintDaysWork;
  state.catalog = data.catalog;
  state.metricsCatalog = data.metricsCatalog || [];
  state.config = data.config;
  state.actuals = data.actuals;
  state.totalWeights = data.totalWeights;
  renderTable();
  renderPeriodOptions();
}

editTargetsBtn.addEventListener("click", openTargetsDialog);
editMetricTargetsBtn.addEventListener("click", openMetricTargetsDialog);
reportBtn.addEventListener("click", loadReport);
planBtn.addEventListener("click", openPlanDialog);
refreshReportBtn.addEventListener("click", loadReport);
cancelTargetsBtn.addEventListener("click", () => targetsDialog.close());
cancelMetricTargetsBtn.addEventListener("click", () => metricTargetsDialog.close());
cancelActualsBtn.addEventListener("click", () => actualsDialog.close());
closePlanBtn.addEventListener("click", () => planDialog.close());
targetsForm.addEventListener("submit", saveTargets);
metricTargetsForm.addEventListener("submit", saveMetricTargets);
actualsForm.addEventListener("submit", saveActuals);
planForm.addEventListener("submit", (event) => event.preventDefault());

tableBody.addEventListener("click", (event) => {
  const target = event.target;
  if (!(target instanceof HTMLElement)) return;
  const sprint = target.dataset.sprint;
  if (!sprint) return;
  openActualsDialog(Number(sprint));
});

loadState().catch((error) => alert(error.message));
