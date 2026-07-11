Custom checkbox (rounded square, solid blue fill when checked) — used for legal-consent rows in Checkout and multi-select filters in tables.

```jsx
<Checkbox checked={agree} onChange={()=>setAgree(!agree)} label={<>Принимаю <a href="#">условия</a></>} />
```
