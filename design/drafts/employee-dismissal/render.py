"""Build the filter proposal from the existing employee screen and project icons."""
from html import escape
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ICON_SOURCE = (ROOT / "apps/internal-ui/src/shared/icons.tsx").read_text(encoding="utf-8")
NAV_SOURCE = (ROOT / "apps/internal-ui/src/layout/NavigationIcon.tsx").read_text(encoding="utf-8")
SKILL_SOURCE = (ROOT / "apps/internal-ui/src/features/skills/SkillGlyph.tsx").read_text(encoding="utf-8")
P = "#0f9b8e"
INK = "#262626"
MUTED = "#8c8c8c"
PARTS = []


def box(x, y, w, h, fill, radius=0, stroke="none"):
    PARTS.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}"/>')


def text(x, y, value, size=13, color=INK, weight=400, extra=""):
    PARTS.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{weight}" {extra}>{escape(value)}</text>')


def line(x1, y1, x2, y2, color="#f0f0f0"):
    PARTS.append(f'<path d="M{x1} {y1}H{x2}" stroke="{color}"/>' if y1 == y2 else f'<path d="M{x1} {y1}L{x2} {y2}" stroke="{color}"/>')


def circle(x, y, radius, color):
    PARTS.append(f'<circle cx="{x}" cy="{y}" r="{radius}" fill="{color}"/>')


def icon(name, x, y, size=17, color=INK):
    if name == "stats" or name == "help":
        path = re.search(rf'{name}: "([^"]+)"', NAV_SOURCE).group(1)
        content = f'<path d="{path}"/>'
    elif name == "skill":
        content = re.search(r'<path[^>]+/>', SKILL_SOURCE).group(0)
    elif name == "robot":
        source = next((ROOT / "packages/ui/src").rglob("AgentIcon.tsx")).read_text(encoding="utf-8")
        content = "".join(re.findall(r'<(?:path|circle|rect|line|polyline)\b[^>]+/>', source))
    elif name == "workflow":
        content = '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/><path d="M17.5 14V6.5a1 1 0 0 0-1-1H10M6.5 10v7.5a1 1 0 0 0 1 1H14"/>'
    else:
        match = re.search(rf'^\s+{name}: (.*),$', ICON_SOURCE, re.M)
        content = match.group(1).replace("<>", "").replace("</>", "")
    content = content.replace("strokeWidth", "stroke-width").replace("strokeLinecap", "stroke-linecap").replace("strokeLinejoin", "stroke-linejoin")
    PARTS.append(f'<svg x="{x}" y="{y}" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{content}</svg>')


def badge(x, y, label, background, foreground, dot=False):
    width = len(label) * 6.1 + (23 if dot else 16)
    box(x, y, width, 22, background, 5)
    if dot:
        circle(x + 10, y + 11, 3, foreground)
    text(x + (19 if dot else 8), y + 15, label, 11.5, foreground, 500)


def dropdown(kind, x, w, label):
    PARTS.append(f'<g id="{kind}-trigger" role="button" tabindex="0" aria-label="{label}" style="cursor:pointer">')
    box(x, 91, w, 34, "#fff", 8, "#e8e8e8")
    text(x + 12, 113, "Все", extra=f'id="{kind}-value"')
    icon("chevron", x + w - 23, 102, 13, MUTED)
    PARTS.append('</g>')


def menu(kind, x, width, values, opened):
    PARTS.append(f'<g id="{kind}-menu" style="display:{"inline" if opened else "none"}" filter="url(#shadow)">')
    box(x, 131, width, 12 + len(values) * 34, "#fff", 8, "#f0f0f0")
    for index, label in enumerate(values):
        y = 137 + index * 34
        PARTS.append(f'<g data-kind="{kind}" data-value="{escape(label)}" role="button" tabindex="0" style="cursor:pointer">')
        box(x + 5, y, width - 10, 32, "#e7f5f4" if index == 0 else "#fff", 5)
        text(x + 13, y + 21, label, color="#0c7f74" if index == 0 else INK)
        if index == 0:
            icon("check", x + width - 27, y + 9, 14, P)
        PARTS.append('</g>')
    PARTS.append('</g>')


def screen(open_menu=None):
    PARTS.clear()
    PARTS.append('<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="945" viewBox="0 0 1920 945" font-family="Segoe UI,Arial,sans-serif"><defs><filter id="shadow" x="-30%" y="-20%" width="160%" height="150%"><feDropShadow dx="0" dy="6" stdDeviation="9" flood-opacity="0.14"/></filter></defs>')
    box(0, 0, 1920, 945, "#f5f6f8")
    box(0, 0, 260, 945, "#fafafa")
    line(259, 0, 259, 945)
    box(14, 16, 28, 28, "#00594d", 7)
    text(21, 38, "S", 25, "white", 600, 'font-style="italic"')
    text(60, 37, "Сурсил", weight=600)
    icon("chevron", 225, 24, 14, MUTED)
    nav = [("Чат", "message", 78), ("Контакты", "user", 117), ("Статистика", "stats", 156),
           ("Агенты", "robot", 207), ("Навыки", "skill", 246), ("Сценарии", "workflow", 284),
           ("AI-провайдеры", "sparkles", 322), ("MCP и HTTP", "server", 360),
           ("База знаний", "book", 412), ("Порталы", "globe", 451), ("Виджеты", "widget", 503),
           ("Мессенджеры", "message", 542), ("Почта", "mail", 580), ("Интеграции", "plug", 619),
           ("Сотрудники", "team", 671), ("Настройки", "settings", 710)]
    for label, glyph, y in nav:
        if label == "Сотрудники":
            box(10, y - 19, 239, 36, "#e7f5f4", 8)
        color = "#0c7f74" if label == "Сотрудники" else INK
        icon(glyph, 20, y - 9, color=color)
        text(48, y + 5, label, color=color)
    for y in (181, 386, 478, 641, 883):
        line(14, y, 246, y)
    icon("help", 20, 849)
    text(48, 862, "Помощь")
    icon("external", 229, 850, 13, "#bfbfbf")
    circle(31, 914, 17, P)
    text(20, 919, "АН", 12, "white", 600)
    text(58, 910, "Андрей")
    text(58, 928, "◉ Готов · с 17 ноя, 19:41", 11, "#237a3f")
    icon("more", 225, 907, 16, MUTED)
    text(512, 49, "Сотрудники", 20, "#1f1f1f", 700)
    text(512, 72, "Роли и группы · показано 2 из 2", 13, MUTED)
    box(1484, 26, 184, 34, P, 8)
    icon("team", 1497, 35, 16, "white")
    text(1521, 48, "Добавить сотрудника", 13, "white", 600)
    box(512, 91, 300, 34, "#fff", 8, "#e8e8e8")
    icon("search", 524, 100, 15, "#bfbfbf")
    text(547, 113, "Поиск по имени, email, должности…", 13, "#bfbfbf")
    box(782, 99, 18, 18, "#f5f5f5", 3)
    text(789, 112, "/", 11, MUTED)
    text(826, 113, "Роль", 12.5, MUTED)
    dropdown("role", 862, 145, "Роль")
    text(1021, 113, "Статус", 12.5, MUTED)
    dropdown("status", 1073, 132, "Статус")
    text(1219, 113, "Группа", 12.5, MUTED)
    dropdown("group", 1269, 120, "Группа")
    text(1403, 113, "Рабочий статус", 12.5, MUTED)
    dropdown("work", 1502, 65, "Рабочий статус")
    text(1600, 113, "Сбросить", 13, MUTED)
    box(512, 142, 1156, 198, "white", 12, "#f0f0f0")
    box(513, 143, 1154, 35, "#fafafa", 11)
    headings = [(532,"СОТРУДНИК"),(710,"РОЛЬ"),(934,"ДОЛЖНОСТЬ"),(1049,"ГРУППЫ"),
                (1176,"РАБОЧИЙ СТАТУС"),(1389,"ДОСТУП"),(1503,"ВХОД")]
    for x, label in headings:
        text(x, 164, label, 11, MUTED, 600)
    for index, data in enumerate([("АД","Администратор","admin@sursil.ru","Владелец","Владелец","Недоступен","11 ч назад"),
                                  ("АН","Андрей","andrey@edevs.tech","Администратор","Интегратор","Готов принимать","1 ч назад")]):
        initials, name, email, role, position, work, login = data
        y = 178 + index * 62
        line(513, y, 1667, y)
        circle(550, y + 31, 18, "#c4456b" if index == 0 else "#4c6ef0")
        text(539, y + 36, initials, 12, "white", 600)
        circle(565, y + 44, 4, "#bfbfbf" if index == 0 else "#52c41a")
        text(581, y + 28, name, 13.5, weight=600)
        text(581, y + 45, email, 11.5, MUTED)
        badge(710, y + 20, role, "#e7f5f4" if index == 0 else "#ece4f5", "#0c7f74" if index == 0 else "#722ed1")
        text(934, y + 36, position)
        if index == 0:
            text(1049, y + 36, "Без группы", 12.5, "#bfbfbf")
        else:
            badge(1049, y + 20, "Операторы", "#f5f5f5", INK, True)
            circle(1059, y + 31, 3, "#2aa876")
        icon("moon" if index == 0 else "check", 1176, y + (24 if index == 0 else 15), 13, MUTED if index == 0 else "#52c41a")
        text(1194, y + (36 if index == 0 else 28), work, 12.5, MUTED if index == 0 else "#237a3f")
        if index:
            text(1176, y + 46, "с 17 ноя, 19:41", 11, MUTED)
        badge(1389, y + 20, "Активен", "#edf8e9", "#237a3f", True)
        text(1503, y + 36, login, 12.5, MUTED)
        icon("more", 1624, y + 23, 16, MUTED)
    line(513, 302, 1667, 302)
    text(532, 326, "Показано 2 из 2", 12, MUTED)
    text(1174, 326, "Точка на фото — приложение открыто. Рабочий статус сотрудник меняет только сам.", 11.5, MUTED)
    menu("role", 862, 186, ["Все","Владелец","Администратор","Супервизор","Сотрудник"], open_menu == "role")
    menu("status", 1073, 182, ["Все","Активен","Приглашён","Заблокирован","Уволен"], open_menu == "status")
    if open_menu == "dismissal":
        box(0, 0, 1920, 945, "#00000066")
        PARTS.append('<g filter="url(#shadow)">')
        box(730, 324, 460, 265, "#fff", 12)
        PARTS.append('</g>')
        circle(770, 367, 21, "#fff2f0")
        icon("errorCircle", 759, 356, 22, "#ff4d4f")
        text(804, 367, "Уволить сотрудника?", 18, "#1f1f1f", 600)
        for index, value in enumerate([
            "Андрей потеряет доступ к этой организации.",
            "Открытые обращения вернутся в очередь.",
            "История работы и доступ к другим",
            "организациям сохранятся.",
        ]):
            text(804, 400 + index * 23, value, 13, "#595959")
        line(730, 518, 1190, 518)
        box(977, 537, 84, 34, "#fff", 8, "#d9d9d9")
        text(994, 559, "Отмена", 13, "#595959", 500)
        box(1071, 537, 95, 34, "#fff", 8, "#ff4d4f")
        text(1096, 559, "Уволить", 13, "#cf1322", 600)
    PARTS.append('</svg>')
    return "\n".join(PARTS)


if __name__ == "__main__":
    for state in ("closed", "role", "status", "dismissal"):
        (HERE / f"screen-{state}.svg").write_text(screen(None if state == "closed" else state), encoding="utf-8")
