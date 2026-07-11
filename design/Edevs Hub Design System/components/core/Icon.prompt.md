A single reusable stroke-icon glyph, drawn from the exact icon paths used across the Hub/Web Chat/Checkout baseline (Feather/Lucide-style outline, 1.8 stroke).

```jsx
<Icon name="departments" size={17} color="#595959" />
```

Notable: `strokeWidth` defaults to 1.8 to match nav icons; bump to 2–2.2 for small/bold contexts (buttons, close icons). Unknown `name` renders nothing — check `ICON_NAMES` for the full set.
