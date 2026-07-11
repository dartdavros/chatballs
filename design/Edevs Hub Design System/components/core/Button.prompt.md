The Hub's single button primitive — one primary accent per screen/context, everything else recedes.

```jsx
<Button variant="primary" size="md" onClick={save}>Сохранить</Button>
<Button variant="secondary">Отмена</Button>
```

Variants: `primary` (solid `--primary`, colored shadow — the one CTA per context), `secondary` (white + border, blue on hover), `ghost` (borderless, gray hover fill), `danger` (destructive red, requires confirmation per ADR-HUB-0013 accessibility rules). Sizes: `sm` 30px, `md` 36px (default), `lg` 44px (auth/checkout primary actions).
