from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

SPRINT_COUNT = 9
SPRINT_DAYS_CALENDAR = 30
SPRINT_DAYS_WORK = 20

SPRINT_CATALOG = [
    {
        "id": 1,
        "title": "Материалы и развертывание",
        "executorWork": "Материалы, план работ, инструкции по развертыванию.",
        "customerWork": "Ознакомление и развертывание 2 копий системы.",
        "metricName": "Готовность среды развертывания (%)",
        "dependencies": [],
    },
    {
        "id": 2,
        "title": "ПЛМ и ввод РКД",
        "executorWork": "Обучение работе с ПЛМ.",
        "customerWork": "Ввод изделий и листов РКД.",
        "metricName": "Количество изделий, введенных в РКД",
        "dependencies": [],
    },
    {
        "id": 3,
        "title": "Цифровой двойник производства",
        "executorWork": "Обучение формированию цифрового двойника.",
        "customerWork": "Ввод участков цифрового двойника.",
        "metricName": "Количество настроенных участков",
        "dependencies": [],
    },
    {
        "id": 4,
        "title": "Технологические карты",
        "executorWork": "Обучение формированию технологических карт.",
        "customerWork": "Ввод технологических карт по изделиям.",
        "metricName": "Количество технологических карт",
        "dependencies": [2, 3],
    },
    {
        "id": 5,
        "title": "Подразделение МТО",
        "executorWork": "Обучение МТО.",
        "customerWork": "Номенклатура, дубли/аналоги, связь с 1С.",
        "metricName": "Количество номенклатурных позиций МТО",
        "dependencies": [2],
    },
    {
        "id": 6,
        "title": "Склад",
        "executorWork": "Обучение подразделения Склад.",
        "customerWork": "Цифровой двойник складов, ввод остатков.",
        "metricName": "Количество позиций с внесенными остатками",
        "dependencies": [2],
    },
    {
        "id": 7,
        "title": "ОТК / Служба качества",
        "executorWork": "Обучение ОТК.",
        "customerWork": "Перечень входного контроля и параметры контроля.",
        "metricName": "Количество позиций входного контроля",
        "dependencies": [2, 4],
    },
    {
        "id": 8,
        "title": "ПДО / Начальник производства",
        "executorWork": "Обучение планированию производства.",
        "customerWork": "Формирование контрольных заказов.",
        "metricName": "Количество контрольных заказов",
        "dependencies": [2, 3, 4, 5, 6],
    },
    {
        "id": 9,
        "title": "Финансовый блок и интеграция 1С",
        "executorWork": "Обучение финансовому блоку.",
        "customerWork": "Интеграция с 1С, миграция остатков и документов.",
        "metricName": "Процент интеграции с 1С",
        "dependencies": [2, 3, 4, 5, 6, 7, 8],
    },
]

METRICS_CATALOG = [
    {"id": sprint["id"], "name": sprint["metricName"]}
    for sprint in SPRINT_CATALOG
]

DEFAULT_WEIGHTS = {
    1: {"executor": 6.0, "customer": 5.0},
    2: {"executor": 6.0, "customer": 5.0},
    3: {"executor": 5.0, "customer": 6.0},
    4: {"executor": 6.0, "customer": 6.0},
    5: {"executor": 5.0, "customer": 6.0},
    6: {"executor": 5.0, "customer": 6.0},
    7: {"executor": 5.0, "customer": 6.0},
    8: {"executor": 6.0, "customer": 6.0},
    9: {"executor": 4.0, "customer": 6.0},
}


def _build_default_state():
    config = {}
    actuals = {}
    for sprint in SPRINT_CATALOG:
        sprint_id = sprint["id"]
        key = str(sprint_id)
        metric_id = sprint_id
        config[key] = {
            "executorWeight": DEFAULT_WEIGHTS[sprint_id]["executor"],
            "customerWeight": DEFAULT_WEIGHTS[sprint_id]["customer"],
            "tasks": [
                {
                    "metricId": metric_id,
                    "months": 1,
                    "target": 0.0,
                }
            ],
        }
        actuals[key] = {
            "executorProgress": 0.0,
            "metricActuals": {str(metric_id): 0.0},
            "notes": "",
        }
    return {"config": config, "actuals": actuals}


state = _build_default_state()


def _to_float(value, fallback=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _normalize_tasks(raw_tasks, previous_tasks=None):
    previous_targets = {}
    if previous_tasks:
        for task in previous_tasks:
            metric_id = int(_to_float(task.get("metricId"), 0))
            if metric_id > 0:
                previous_targets[metric_id] = max(_to_float(task.get("target"), 0), 0)

    normalized = []
    seen = set()
    for task in raw_tasks or []:
        metric_id = int(_to_float(task.get("metricId"), 0))
        if metric_id < 1 or metric_id > len(METRICS_CATALOG) or metric_id in seen:
            continue
        seen.add(metric_id)
        months = int(_to_float(task.get("months"), 1))
        normalized.append(
            {
                "metricId": metric_id,
                "months": max(1, min(months, SPRINT_COUNT)),
                "target": max(_to_float(task.get("target"), previous_targets.get(metric_id, 0.0)), 0),
            }
        )
    return normalized


@app.route("/")
def index():
    return render_template("index.html")


@app.get("/api/state")
def get_state():
    total_weights = 0.0
    for sprint in SPRINT_CATALOG:
        key = str(sprint["id"])
        sprint_cfg = state["config"].get(key, {})
        total_weights += _to_float(sprint_cfg.get("executorWeight"))
        total_weights += _to_float(sprint_cfg.get("customerWeight"))
    return jsonify(
        {
            "sprintCount": SPRINT_COUNT,
            "sprintDaysCalendar": SPRINT_DAYS_CALENDAR,
            "sprintDaysWork": SPRINT_DAYS_WORK,
            "catalog": SPRINT_CATALOG,
            "metricsCatalog": METRICS_CATALOG,
            "config": state["config"],
            "actuals": state["actuals"],
            "totalWeights": round(total_weights, 2),
        }
    )


@app.post("/api/config")
def save_config():
    payload = request.get_json(silent=True) or {}
    config = payload.get("config", {})

    normalized = {}
    total_weights = 0.0
    for sprint in SPRINT_CATALOG:
        key = str(sprint["id"])
        sprint_cfg = config.get(key, {})
        old_cfg = state["config"].get(key, {})
        old_tasks = old_cfg.get("tasks", [])
        tasks = _normalize_tasks(sprint_cfg.get("tasks", []), old_tasks)
        executor_weight = max(
            min(_to_float(sprint_cfg.get("executorWeight"), DEFAULT_WEIGHTS[sprint["id"]]["executor"]), 100),
            0,
        )
        customer_weight = max(
            min(_to_float(sprint_cfg.get("customerWeight"), DEFAULT_WEIGHTS[sprint["id"]]["customer"]), 100),
            0,
        )
        normalized[key] = {
            "executorWeight": executor_weight,
            "customerWeight": customer_weight,
            "tasks": tasks,
        }
        total_weights += executor_weight + customer_weight

    if abs(total_weights - 100.0) > 0.01:
        return jsonify({"error": "Сумма весов Исполнителя и Заказчика должна быть ровно 100."}), 400

    state["config"] = normalized

    return jsonify({"ok": True})


@app.post("/api/targets")
def save_targets():
    payload = request.get_json(silent=True) or {}
    targets = payload.get("targets", {})
    for sprint in SPRINT_CATALOG:
        key = str(sprint["id"])
        cfg = state["config"].get(key, {})
        tasks = cfg.get("tasks", [])
        sprint_targets = targets.get(key, {})
        for task in tasks:
            metric_key = str(task["metricId"])
            if metric_key in sprint_targets:
                target_data = sprint_targets.get(metric_key, {})
                if isinstance(target_data, dict):
                    task["target"] = max(_to_float(target_data.get("target"), task.get("target", 0)), 0)
                    task["months"] = max(
                        1,
                        min(int(_to_float(target_data.get("months"), task.get("months", 1))), SPRINT_COUNT),
                    )
                else:
                    # Backward compatibility with old payload format: {metricId: target}
                    task["target"] = max(_to_float(target_data, task.get("target", 0)), 0)
    return jsonify({"ok": True})


@app.post("/api/actuals/<int:sprint_id>")
def save_actuals(sprint_id):
    if sprint_id < 1 or sprint_id > SPRINT_COUNT:
        return jsonify({"error": "Некорректный номер спринта."}), 400

    payload = request.get_json(silent=True) or {}
    values = payload.get("values", {})
    sprint_key = str(sprint_id)
    current = state["actuals"].get(sprint_key, {})
    current_actuals = current.get("metricActuals", {})
    incoming_actuals = values.get("metricActuals", {})
    metric_actuals = {}
    for metric in METRICS_CATALOG:
        metric_key = str(metric["id"])
        metric_actuals[metric_key] = max(
            _to_float(incoming_actuals.get(metric_key), current_actuals.get(metric_key, 0)),
            0,
        )
    state["actuals"][sprint_key] = {
        "executorProgress": max(min(_to_float(values.get("executorProgress"), current.get("executorProgress", 0)), 100), 0),
        "metricActuals": metric_actuals,
        "notes": str(values.get("notes", current.get("notes", ""))).strip(),
    }

    return jsonify({"ok": True})


@app.post("/api/report")
def report():
    payload = request.get_json(silent=True) or {}
    try:
        period = int(payload.get("period", SPRINT_COUNT))
    except (TypeError, ValueError):
        period = SPRINT_COUNT
    period = max(1, min(period, SPRINT_COUNT))

    considered_sprints = [str(i) for i in range(1, period + 1)]
    max_score_period = 0.0
    actual_score = 0.0
    delayed_items = []
    sprint_details = []
    timeline_items = []
    executor_timeline_items = []

    # Debts from earlier sprints included in selected period.
    debts = []

    for sprint in SPRINT_CATALOG:
        sprint_id = sprint["id"]
        if sprint_id > period:
            continue
        key = str(sprint_id)
        cfg = state["config"].get(key, {})
        act = state["actuals"].get(key, {})
        tasks = cfg.get("tasks", [])
        executor_weight = _to_float(cfg.get("executorWeight"))
        customer_weight = _to_float(cfg.get("customerWeight"))
        metric_actuals = act.get("metricActuals", {})
        executor_progress = max(min(_to_float(act.get("executorProgress")), 100), 0)
        progress_values = []
        metrics_summary = []
        for task in tasks:
            metric_id = task.get("metricId")
            metric_name = next((m["name"] for m in METRICS_CATALOG if m["id"] == metric_id), f"Метрика {metric_id}")
            metric_target = _to_float(task.get("target"))
            metric_actual = _to_float(metric_actuals.get(str(metric_id), 0))
            metric_progress = 0.0 if metric_target == 0 else min((metric_actual / metric_target) * 100, 100)
            progress_values.append(metric_progress)
            metrics_summary.append(
                {
                    "metricId": metric_id,
                    "metricName": metric_name,
                    "target": round(metric_target, 2),
                    "actual": round(metric_actual, 2),
                    "progress": round(metric_progress, 2),
                    "months": int(_to_float(task.get("months"), 1)),
                }
            )
            timeline_items.append(
                {
                    "headSprint": sprint_id,
                    "metricId": metric_id,
                    "metricName": metric_name,
                    "startSprint": sprint_id,
                    "durationMonths": int(_to_float(task.get("months"), 1)),
                    "progress": round(metric_progress, 2),
                }
            )
        executor_timeline_items.append(
            {
                "headSprint": sprint_id,
                "metricId": sprint_id,
                "metricName": f"Исполнитель: {sprint['title']}",
                "startSprint": sprint_id,
                "durationMonths": 1,
                "progress": round(executor_progress, 2),
            }
        )
        metric_progress = sum(progress_values) / len(progress_values) if progress_values else 0.0

        customer_progress = metric_progress
        sprint_max = executor_weight + customer_weight
        sprint_score = (executor_weight * executor_progress / 100.0) + (customer_weight * customer_progress / 100.0)
        sprint_percent = 0.0 if sprint_max == 0 else (sprint_score / sprint_max) * 100

        max_score_period += sprint_max
        actual_score += sprint_score

        dependencies_blocking = []
        for dep in sprint["dependencies"]:
            dep_actual = state["actuals"].get(str(dep), {})
            dep_cfg = state["config"].get(str(dep), {})
            dep_tasks = dep_cfg.get("tasks", [])
            dep_progress_values = []
            dep_actuals = dep_actual.get("metricActuals", {})
            for dep_task in dep_tasks:
                dep_metric_target = _to_float(dep_task.get("target"), 1)
                dep_metric_actual = _to_float(dep_actuals.get(str(dep_task.get("metricId")), 0), 0)
                dep_metric_progress = 0 if dep_metric_target == 0 else min((dep_metric_actual / dep_metric_target) * 100, 100)
                dep_progress_values.append(dep_metric_progress)
            dep_metric_progress = (
                sum(dep_progress_values) / len(dep_progress_values) if dep_progress_values else 0
            )
            if dep_metric_progress < 95:
                dependencies_blocking.append(dep)

        if sprint_percent < 100:
            debts.append(
                {
                    "sprint": sprint_id,
                    "title": sprint["title"],
                    "gapPoints": round(sprint_max - sprint_score, 2),
                }
            )

        if executor_progress < 100:
            delayed_items.append(
                {
                    "sprint": sprint_id,
                    "area": "Исполнитель",
                    "problem": f"Невыполнение этапов обучения и контроля ({executor_progress:.1f}%).",
                    "severity": round(100 - executor_progress, 2),
                }
            )
        if customer_progress < 100:
            delayed_items.append(
                {
                    "sprint": sprint_id,
                    "area": "Заказчик",
                    "problem": (
                        f"Невыполнение по выбранным метрикам: "
                        f"{customer_progress:.1f}%."
                    ),
                    "severity": round(100 - customer_progress, 2),
                }
            )
        if dependencies_blocking:
            delayed_items.append(
                {
                    "sprint": sprint_id,
                    "area": "Зависимости",
                    "problem": f"Спринт опирается на незавершенные спринты: {', '.join(map(str, dependencies_blocking))}.",
                    "severity": 100.0,
                }
            )

        sprint_details.append(
            {
                "sprint": sprint_id,
                "title": sprint["title"],
                "executorStatus": round(executor_progress, 2),
                "customerStatus": round(customer_progress, 2),
                "metrics": metrics_summary,
                "sprintScore": round(sprint_score, 2),
                "sprintMax": round(sprint_max, 2),
                "notes": act.get("notes", ""),
            }
        )

    delayed_items.sort(key=lambda item: item["severity"], reverse=True)
    debts.sort(key=lambda item: item["gapPoints"], reverse=True)

    # Projection by current implementation velocity.
    completed_sprints = len(considered_sprints)
    score_per_sprint = 0.0 if completed_sprints == 0 else actual_score / completed_sprints
    full_max_score = 0.0
    for sprint in SPRINT_CATALOG:
        key = str(sprint["id"])
        cfg = state["config"].get(key, {})
        full_max_score += _to_float(cfg.get("executorWeight")) + _to_float(cfg.get("customerWeight"))

    remaining_score = max(full_max_score - actual_score, 0)
    if score_per_sprint <= 0:
        forecast_text = "Недостаточно данных для прогноза: нет зафиксированного прогресса."
    else:
        estimated_remaining_sprints = remaining_score / score_per_sprint
        estimated_calendar_days = estimated_remaining_sprints * SPRINT_DAYS_CALENDAR
        forecast_text = (
            f"При текущем темпе потребуется около {estimated_remaining_sprints:.1f} спринтов "
            f"(примерно {estimated_calendar_days:.0f} календарных дней) для достижения 100 баллов."
        )

    recommendations = []
    for item in delayed_items[:5]:
        if item["area"] == "Заказчик":
            recommendations.append(
                f"Спринт {item['sprint']}: усилить ресурс Заказчика на ввод данных и закрытие метрик."
            )
        elif item["area"] == "Исполнитель":
            recommendations.append(
                f"Спринт {item['sprint']}: увеличить плотность обучения и контрольных сессий Исполнителя."
            )
        else:
            recommendations.append(
                f"Спринт {item['sprint']}: закрыть зависимости до продолжения работ текущего спринта."
            )

    if not recommendations:
        recommendations.append("Критических отклонений нет, продолжать текущий темп внедрения.")

    progress = 0.0 if full_max_score == 0 else min((actual_score / full_max_score) * 100, 100)

    return jsonify(
        {
            "period": period,
            "progressPercent": round(progress, 2),
            "scoreActual": round(actual_score, 2),
            "scoreMax": round(full_max_score, 2),
            "scorePeriodMax": round(max_score_period, 2),
            "delayedItems": delayed_items,
            "debts": debts,
            "forecast": forecast_text,
            "recommendations": recommendations,
            "sprintDetails": sprint_details,
            "timeline": timeline_items,
            "customerTimeline": timeline_items,
            "executorTimeline": executor_timeline_items,
        }
    )


if __name__ == "__main__":
    app.run(debug=True)
