Vertical step tracker that keeps payment and product-delivery states visually separate — never implies "paid" also means "delivered" (SPEC-HUB-0007).

```jsx
<CommerceStatusTimeline steps={[
  {label:'Оплата подтверждена · ₽95 040', state:'done'},
  {label:'Подготовка рабочих мест', state:'active'},
]} />
```
