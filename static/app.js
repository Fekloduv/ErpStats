const state = {
  sprintCount: 9,
  sprintDaysCalendar: 30,
  sprintDaysWork: 20,
  catalog: [],
  config: {},
  actuals: {},
  totalWeights: 0,
};

const tableHead = document.querySelector("#metricsTable thead");
const tableBody = document.querySelector("#metricsTable tbody");
const editTargetsBtn = document.getElementById("editTargetsBtn");
const reportBtn = document.getElementById("reportBtn");
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

const targetsDialog = document.getElementById("targetsDialog");
const targetsForm = document.getElementById("targetsForm");
const targetsGrid = document.getElementById("targetsGrid");
const cancelTargetsBtn = document.getElementById("cancelTargetsBtn");

const actualsDialog = document.getElementById("actualsDialog");
const actualsForm = document.getElementById("actualsForm");
const actualsTitle = document.getElementById("actualsTitle");
const actualsFields = document.getElementById("actualsFields");
const cancelActualsBtn = document.getElementById("cancelActualsBtn");

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

    const metricTarget = Number(cfg.metricTarget || 0);
    const metricActual = Number(act.metricActual || 0);
    const metricProgress = metricTarget > 0 ? Math.min((metricActual / metricTarget) * 100, 100) : 0;
    const executorProgress = Number(act.executorProgress || 0);
    const customerProgress = metricProgress;

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
        <div>${sprintItem?.metricName || "Метрика"}: <strong>${numberFormat(metricTarget)}</strong></div>
      </td>
      <td>
        <div>Исполнитель: <strong>${numberFormat(executorProgress)}%</strong></div>
        <div>Заказчик (авто по метрике): <strong>${numberFormat(customerProgress)}%</strong></div>
        <div>Метрика факт: <strong>${numberFormat(metricActual)}</strong></div>
      </td>
      <td><strong class="${statusClass}">${numberFormat(sprintPercent)}%</strong><br><small>${numberFormat(earnedScore)} / ${numberFormat(maxScore)} баллов</small></td>
      <td><button class="btn btn-secondary" data-sprint="${sprint}">Внести данные</button></td>
    `;
    tableBody.appendChild(row);
  }

  weightsSummary.textContent = `Сумма весов по всем спринтам: ${numberFormat(state.totalWeights)} баллов (рекомендуется 100).`;
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
    const row = document.createElement("div");
    row.className = "target-row";
    row.innerHTML = `
      <strong>Спринт ${sprint}: ${sprintItem?.title || ""}</strong>
      <div class="target-metrics">
        <label>
          Вес Исполнителя
          <input type="number" min="0" step="0.01" data-sprint="${sprint}" data-field="executorWeight" value="${cfg.executorWeight ?? 0}">
        </label>
        <label>
          Вес Заказчика
          <input type="number" min="0" step="0.01" data-sprint="${sprint}" data-field="customerWeight" value="${cfg.customerWeight ?? 0}">
        </label>
        <label>
          Цель: ${sprintItem?.metricName || "Метрика"}
          <input type="number" min="0" step="0.01" data-sprint="${sprint}" data-field="metricTarget" value="${cfg.metricTarget ?? 0}">
        </label>
      </div>
    `;
    targetsGrid.appendChild(row);
  }
  targetsDialog.showModal();
}

function openActualsDialog(sprint) {
  activeSprint = sprint;
  const sprintKey = String(sprint);
  const sprintItem = state.catalog.find((item) => item.id === sprint);
  const cfg = state.config[sprintKey] || {};
  const act = state.actuals[sprintKey] || {};

  actualsTitle.textContent = `Внести данные: спринт ${sprint} (${sprintItem?.title || ""})`;
  actualsFields.innerHTML = `
    <label>
      Исполнитель: выполнение этапов (0-100%)
      <input type="number" min="0" max="100" step="0.01" name="executorProgress" value="${act.executorProgress ?? 0}">
    </label>
    <label>
      Фактическое значение: ${sprintItem?.metricName || "метрика"} (план: ${numberFormat(cfg.metricTarget)})
      <input type="number" min="0" step="0.01" name="metricActual" value="${act.metricActual ?? 0}">
    </label>
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
      metricTarget: 0,
    };
  }

  inputs.forEach((input) => {
    const sprint = input.dataset.sprint;
    const field = input.dataset.field;
    config[sprint][field] = Number(input.value || 0);
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

async function saveActuals(event) {
  event.preventDefault();
  if (!activeSprint) return;

  const formData = new FormData(actualsForm);
  const values = {
    executorProgress: Number(formData.get("executorProgress") || 0),
    metricActual: Number(formData.get("metricActual") || 0),
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
      const row = document.createElement("tr");
      row.innerHTML = `
        <td>${item.sprint}. ${item.title}</td>
        <td>${numberFormat(item.executorStatus)}%</td>
        <td>${numberFormat(item.customerStatus)}%</td>
        <td>${item.metricName}: ${numberFormat(item.metricActual)} / ${numberFormat(item.metricTarget)}</td>
        <td>${numberFormat(item.sprintScore)} / ${numberFormat(item.sprintMax)}</td>
        <td>${item.notes || "-"}</td>
      `;
      reportDetailsBody.appendChild(row);
    });
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
  state.config = data.config;
  state.actuals = data.actuals;
  state.totalWeights = data.totalWeights;
  renderTable();
  renderPeriodOptions();
}

editTargetsBtn.addEventListener("click", openTargetsDialog);
reportBtn.addEventListener("click", loadReport);
refreshReportBtn.addEventListener("click", loadReport);
cancelTargetsBtn.addEventListener("click", () => targetsDialog.close());
cancelActualsBtn.addEventListener("click", () => actualsDialog.close());
targetsForm.addEventListener("submit", saveTargets);
actualsForm.addEventListener("submit", saveActuals);

tableBody.addEventListener("click", (event) => {
  const target = event.target;
  if (!(target instanceof HTMLElement)) return;
  const sprint = target.dataset.sprint;
  if (!sprint) return;
  openActualsDialog(Number(sprint));
});

loadState().catch((error) => alert(error.message));
