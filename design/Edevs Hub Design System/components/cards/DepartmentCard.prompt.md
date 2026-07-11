The Command Center's headline card — one per company department, showing name, health, a one-line human summary, and the single "open department" CTA.

```jsx
<DepartmentCard name="Продажи" meta="Анна Котова · 4 сотрудника" level="ok" summary="AI ведёт большинство диалогов." onOpen={go}>
  <MetricGrid .../>
</DepartmentCard>
```

Nest `MetricCard` grids as `children` for the "дialogs now" / "commerce" detail rows.
