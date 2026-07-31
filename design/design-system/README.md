# CustoCRM Design System

Статический справочник текущего frontend UI. React, сборка и установка зависимостей не требуются.

## Открытие в Windows PowerShell

Из корня репозитория:

```powershell
Start-Process .\apps\internal-ui\design-system\index.html
```

Для просмотра через локальный HTTP-сервер:

```powershell
python -m http.server 8080 --directory .\apps\internal-ui\design-system
Start-Process http://localhost:8080
```

## Состав

- `index.html` — оглавление;
- `foundations.html` — токены;
- `components.html` — базовые controls;
- `data-display.html` — статусы и представление данных;
- `patterns.html` — таблицы, состояния, меню и dialogs;
- `layouts.html` — типовые компоновки экранов;
- `inventory.html` — поисковый реестр;
- `inventory.json` — машиночитаемая инвентаризация.

Справочник автономен и не подключён к production bundle приложения.
