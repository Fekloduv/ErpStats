import io
import importlib
from datetime import datetime

from flask import Flask, jsonify, render_template, request, send_file

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
    period = _parse_period(payload.get("period", SPRINT_COUNT))

    return jsonify(_build_report_payload(period))


def _parse_period(value):
    try:
        period = int(value)
    except (TypeError, ValueError):
        period = SPRINT_COUNT
    return max(1, min(period, SPRINT_COUNT))


def _build_report_payload(period):

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

    return {
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


def _load_reportlab():
    pagesizes = importlib.import_module("reportlab.lib.pagesizes")
    pdfmetrics = importlib.import_module("reportlab.pdfbase.pdfmetrics")
    ttfonts = importlib.import_module("reportlab.pdfbase.ttfonts")
    canvas_module = importlib.import_module("reportlab.pdfgen.canvas")
    return pagesizes, pdfmetrics, ttfonts, canvas_module


def _setup_pdf_font(pdfmetrics, ttfonts):
    font_name = "Helvetica"
    candidates = [
        r"C:\Windows\Fonts\arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        try:
            pdfmetrics.registerFont(ttfonts.TTFont("AppUnicode", path))
            font_name = "AppUnicode"
            break
        except Exception:
            continue
    return font_name


def _timeline_label(text):
    value = str(text or "")
    if value.startswith("Исполнитель: "):
        return value.replace("Исполнитель: ", "", 1)
    if value.startswith("Исполнитель "):
        return value.replace("Исполнитель ", "", 1)
    return value


def _draw_timeline_landscape_page(pdf, pagesizes, font_name, title, period, customer_items, executor_items, show_progress=True):
    landscape_a4 = pagesizes.landscape(pagesizes.A4)
    pdf.showPage()
    pdf.setPageSize(landscape_a4)
    page_w, page_h = landscape_a4

    left = 18
    top = page_h - 22
    label_w = 74
    right_margin = 14
    bottom_margin = 18
    lane_h = 18
    lane_gap = 3
    row_gap = 4
    max_cols = max(1, int(period))
    lane_rows = max_cols * 2

    def fit_lines(text, max_width, font_size, max_lines=2):
        words = str(text or "").split()
        if not words:
            return []
        lines = []
        current = ""
        for word in words:
            candidate = (current + " " + word).strip()
            if pdf.stringWidth(candidate, font_name, font_size) <= max_width:
                current = candidate
                continue
            if current:
                lines.append(current)
            current = word
            if len(lines) >= max_lines - 1:
                break
        if current and len(lines) < max_lines:
            lines.append(current)

        consumed = " ".join(lines).split()
        if len(consumed) < len(words):
            last = lines[-1] if lines else ""
            while last and pdf.stringWidth(f"{last}...", font_name, font_size) > max_width:
                last = last[:-1]
            lines[-1] = f"{last}..." if last else "..."
        return lines

    pdf.setFont(font_name, 11)
    pdf.setFillColorRGB(0.12, 0.16, 0.22)
    pdf.drawString(left, top, title)

    usable_w = page_w - left - right_margin - label_w
    cell_w = usable_w / max_cols
    y = top - 18

    # Adapt row height to fit all lanes without clipping.
    available_h = max(60, y - bottom_margin)
    fixed_gaps = lane_rows * lane_gap + max_cols * row_gap + 10
    lane_h = max(12, min(24, int((available_h - fixed_gaps) / max(lane_rows, 1))))
    lane_font = 8 if lane_h <= 15 else 9
    task_font = 6.6 if lane_h <= 15 else 7.4

    pdf.setFont(font_name, lane_font)
    for col in range(1, max_cols + 1):
        x = left + label_w + (col - 1) * cell_w
        pdf.setFillColorRGB(0.25, 0.30, 0.40)
        pdf.drawString(x + 1, y, f"M{col}")
    y -= 10

    for sprint in range(1, max_cols + 1):
        lanes = [
            ("Исп.", [i for i in executor_items if int(i.get("headSprint", 0)) == sprint], (0.75, 0.88, 0.80)),
            ("Зак.", [i for i in customer_items if int(i.get("headSprint", 0)) == sprint], (0.78, 0.84, 0.95)),
        ]

        for lane_name, lane_items, base_color in lanes:
            pdf.setFont(font_name, lane_font)
            pdf.setFillColorRGB(0.20, 0.24, 0.32)
            pdf.drawString(left, y + 2, f"С{sprint} {lane_name}")

            for col in range(1, max_cols + 1):
                x = left + label_w + (col - 1) * cell_w
                pdf.setStrokeColorRGB(0.86, 0.89, 0.94)
                pdf.setFillColorRGB(0.97, 0.98, 1.0)
                pdf.rect(x, y - lane_h + 2, cell_w - 1, lane_h, fill=1, stroke=1)

            for item in lane_items:
                start = max(1, int(_to_float(item.get("startSprint"), sprint)))
                duration = max(1, int(_to_float(item.get("durationMonths"), 1)))
                end = min(max_cols, start + duration - 1)
                if start > max_cols:
                    continue
                x = left + label_w + (start - 1) * cell_w + 0.5
                w = max(1.5, (end - start + 1) * cell_w - 1.5)
                progress = max(0.0, min(_to_float(item.get("progress"), 0), 100.0))
                progress_w = w * (progress / 100.0)

                pdf.setStrokeColorRGB(0.55, 0.62, 0.74)
                pdf.setFillColorRGB(*base_color)
                pdf.rect(x, y - lane_h + 2, w, lane_h, fill=1, stroke=1)
                if show_progress and progress_w > 1:
                    pdf.setFillColorRGB(base_color[0] * 0.75, base_color[1] * 0.75, base_color[2] * 0.75)
                    pdf.rect(x, y - lane_h + 2, progress_w, lane_h, fill=1, stroke=0)

                text = _timeline_label(item.get("metricName", ""))
                if show_progress:
                    text = f"{text} ({progress:.0f}%)"
                max_lines = 3 if lane_h >= 18 else 2
                lines = fit_lines(text, max(8, w - 3), task_font, max_lines=max_lines)
                if lines:
                    pdf.setFillColorRGB(0.12, 0.16, 0.22)
                    pdf.setFont(font_name, task_font)
                    text_y = y - lane_h + (lane_h * 0.62 if len(lines) == 1 else lane_h * 0.84)
                    for idx, line in enumerate(lines):
                        pdf.drawString(x + 1, text_y - idx * (task_font + 0.8), line)

            y -= lane_h + lane_gap
        y -= row_gap


@app.get("/api/report/pdf")
def report_pdf():
    period = _parse_period(request.args.get("period", SPRINT_COUNT))
    data = _build_report_payload(period)

    try:
        pagesizes, pdfmetrics, ttfonts, canvas_module = _load_reportlab()
    except ImportError:
        return jsonify({"error": "Для выгрузки PDF установите зависимость: pip install reportlab"}), 500
    A4 = pagesizes.A4
    canvas = canvas_module
    font_name = _setup_pdf_font(pdfmetrics, ttfonts)

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 48
    left = 36

    def write_line(text, size=10, gap=14):
        nonlocal y
        if y < 50:
            pdf.showPage()
            pdf.setFont(font_name, size)
            y = height - 48
        pdf.setFont(font_name, size)
        pdf.drawString(left, y, str(text))
        y -= gap

    def wrap_text(text, size=10, gap=12, max_width=None):
        nonlocal y
        max_width_local = max_width or (width - left * 2)
        words = str(text).split()
        line = ""
        for word in words:
            test = (line + " " + word).strip()
            if pdf.stringWidth(test, font_name, size) <= max_width_local:
                line = test
            else:
                write_line(line, size=size, gap=gap)
                line = word
        if line:
            write_line(line, size=size, gap=gap)

    def ensure_space(required_height, font_size=10):
        nonlocal y
        if y - required_height < 40:
            pdf.showPage()
            pdf.setFont(font_name, font_size)
            y = height - 48

    write_line("Отчёт внедрения ПО «ИСКРА»", size=14, gap=18)
    write_line(f"Дата формирования: {datetime.now().strftime('%d.%m.%Y %H:%M')}", size=9, gap=12)
    write_line(f"Период: {data['period']} спринт(ов)", size=10)
    write_line(
        f"Показатель внедрения: {data['progressPercent']:.2f}% "
        f"({data['scoreActual']:.2f} из {data['scoreMax']:.2f} баллов)",
        size=10,
    )
    write_line("")
    write_line("Работы с нарушением сроков / отставанием:", size=11, gap=14)
    if not data["delayedItems"]:
        write_line("- Нарушений сроков и критических отставаний нет.", size=10)
    else:
        for item in data["delayedItems"][:12]:
            wrap_text(
                f"- Спринт {item['sprint']} [{item['area']}]: {item['problem']} "
                f"(критичность {item['severity']:.1f})",
                size=9,
                gap=11,
            )

    write_line("")
    write_line("Накопленные долги:", size=11, gap=14)
    if not data["debts"]:
        write_line("- Накопленных долгов нет.", size=10)
    else:
        for debt in data["debts"][:10]:
            write_line(
                f"- Спринт {debt['sprint']} ({debt['title']}): дефицит {debt['gapPoints']:.2f} баллов",
                size=9,
                gap=11,
            )

    write_line("")
    write_line("Прогноз:", size=11, gap=14)
    wrap_text(data["forecast"], size=10)
    write_line("")
    write_line("Рекомендации:", size=11, gap=14)
    for rec in data["recommendations"]:
        wrap_text(f"- {rec}", size=10)

    write_line("")
    write_line("Детализация по спринтам:", size=11, gap=14)
    for item in data["sprintDetails"]:
        write_line(
            f"Спринт {item['sprint']}: {item['title']} | "
            f"Исп. {item['executorStatus']:.1f}% | Зак. {item['customerStatus']:.1f}%",
            size=10,
        )
        metrics = item.get("metrics", [])
        for metric in metrics:
            wrap_text(
                f"  • {metric['metricName']}: факт {metric['actual']:.2f} / цель {metric['target']:.2f} "
                f"({metric['progress']:.1f}%), срок {metric['months']} мес.",
                size=9,
                gap=11,
                max_width=width - left * 2 - 10,
            )
        notes = item.get("notes", "").strip()
        if notes:
            wrap_text(f"  Примечание: {notes}", size=9, gap=11)
        y -= 4

    _draw_timeline_landscape_page(
        pdf,
        pagesizes,
        font_name,
        "Диаграмма сроков задач (Исполнитель сверху, Заказчик снизу):",
        data["period"],
        data.get("customerTimeline", []),
        data.get("executorTimeline", []),
    )

    pdf.save()
    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"report_sprint_{period}.pdf",
        mimetype="application/pdf",
    )


@app.get("/api/plan/pdf")
def plan_pdf():
    try:
        pagesizes, pdfmetrics, ttfonts, canvas_module = _load_reportlab()
    except ImportError:
        return jsonify({"error": "Для выгрузки PDF установите зависимость: pip install reportlab"}), 500

    A4 = pagesizes.A4
    canvas = canvas_module
    font_name = _setup_pdf_font(pdfmetrics, ttfonts)
    report_data = _build_report_payload(SPRINT_COUNT)

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 48
    left = 36

    def write_line(text, size=10, gap=14):
        nonlocal y
        if y < 50:
            pdf.showPage()
            pdf.setFont(font_name, size)
            y = height - 48
        pdf.setFont(font_name, size)
        pdf.drawString(left, y, str(text))
        y -= gap

    def wrap_text(text, size=10, gap=12, max_width=None):
        nonlocal y
        max_width_local = max_width or (width - left * 2)
        words = str(text).split()
        line = ""
        for word in words:
            test = (line + " " + word).strip()
            if pdf.stringWidth(test, font_name, size) <= max_width_local:
                line = test
            else:
                write_line(line, size=size, gap=gap)
                line = word
        if line:
            write_line(line, size=size, gap=gap)

    write_line("План внедрения ПО «ИСКРА»", size=14, gap=18)
    write_line(f"Дата формирования: {datetime.now().strftime('%d.%m.%Y %H:%M')}", size=9, gap=12)
    write_line(f"Спринтов в плане: {SPRINT_COUNT}", size=10)
    write_line("")

    for sprint in SPRINT_CATALOG:
        sprint_id = sprint["id"]
        key = str(sprint_id)
        cfg = state["config"].get(key, {})
        tasks = cfg.get("tasks", [])
        write_line(f"Спринт {sprint_id}: {sprint['title']}", size=11, gap=14)
        write_line(
            f"Вес Исполнителя / Заказчика: "
            f"{_to_float(cfg.get('executorWeight')):.2f} / {_to_float(cfg.get('customerWeight')):.2f}",
            size=9,
            gap=11,
        )
        if not tasks:
            write_line("- Метрики не выбраны.", size=9, gap=11)
        else:
            for task in tasks:
                metric_name = next(
                    (m["name"] for m in METRICS_CATALOG if m["id"] == task.get("metricId")),
                    f"Метрика {task.get('metricId')}",
                )
                wrap_text(
                    f"- {metric_name}: цель {_to_float(task.get('target')):.2f}, "
                    f"срок {int(_to_float(task.get('months'), 1))} мес.",
                    size=9,
                    gap=11,
                )
        y -= 2

    _draw_timeline_landscape_page(
        pdf,
        pagesizes,
        font_name,
        "Диаграмма сроков задач плана (Исполнитель сверху, Заказчик снизу):",
        SPRINT_COUNT,
        report_data.get("customerTimeline", []),
        report_data.get("executorTimeline", []),
        show_progress=False,
    )

    pdf.save()
    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name="plan.pdf",
        mimetype="application/pdf",
    )


if __name__ == "__main__":
    app.run(debug=True)
