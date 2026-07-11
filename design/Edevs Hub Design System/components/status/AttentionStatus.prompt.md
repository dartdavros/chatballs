Health/status pill for company and department state — drives the Command Center banner border color, department card status, and page-level scenario switches.

```jsx
<AttentionStatus level="critical" />
```

Levels map 1:1 to the semantic tokens: `ok` → success, `attention` → warning, `critical` → error. Never used as the sole indicator of a destructive action — always paired with a text summary nearby.
