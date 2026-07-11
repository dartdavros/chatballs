The atomic KPI cell — tile these in a CSS grid with 1px gaps on a `--n-8` background to get the hairline-divided metric grid seen in Command Center and Sales Overview.

```jsx
<div style={{display:'grid',gridTemplateColumns:'repeat(4,1fr)',gap:1,background:'var(--n-8)',border:'1px solid var(--n-8)',borderRadius:9,overflow:'hidden'}}>
  <MetricCard label="Открытые диалоги" value={42} />
  <MetricCard label="Ожидают оператора" value={4} valueColor="var(--warning-text)" />
</div>
```

Never adds a trend arrow or icon of its own — value, label, and an optional color/dot are the only inputs (ADR-HUB-0013 forbids oversized/decorated metric cards).
