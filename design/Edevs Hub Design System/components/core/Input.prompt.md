Labeled text field matching the auth/checkout/filter-bar inputs — 42px tall, 9px radius, blue focus ring via border color only (no glow).

```jsx
<Input label="Email" required icon={<Icon name="mail" color="#bfbfbf" size={16}/>} value={v} onChange={e=>set(e.target.value)} />
```

Set `error` + `hint` together for validation messages (errors show inline near the field per ADR-HUB-0013). `icon` is left-aligned (search/mail/lock); `suffix` is right-aligned (password show/hide).
