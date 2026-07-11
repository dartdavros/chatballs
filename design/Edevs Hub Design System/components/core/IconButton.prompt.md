A square icon-only button — topbar actions (notifications, refresh), table row menus.

```jsx
<IconButton label="Уведомления" badge={4}><Icon name="bell" size={18} /></IconButton>
<IconButton bare label="Ещё"><Icon name="moreVertical" size={17} /></IconButton>
```

Always pass `label` — it becomes both the tooltip and the accessible name (icon-only buttons need a text alternative per ADR-HUB-0013 accessibility rules). `bare` drops the border for menu/table contexts.
