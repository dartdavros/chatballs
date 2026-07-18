# Edevs Hub — Design System

Design system for **Edevs**, a Russian product IT company (`edevs.tech`) that builds applied
digital products for narrow professional niches — currently **FoxRay** (cephalometric/TRG
analysis for orthodontists) and **FirePage** (ready-made niche websites on a proprietary CMS,
sold as a one-time license). This design system, however, documents **Edevs Hub**
(`hub.edevs.tech`) — the internal company platform that runs sales, support, AI agents, and
commerce for those products, plus the two small public-facing surfaces it exposes (Web Chat
widget and Checkout).

## Sources

Everything here was extracted from the attached codebase, mounted read-only at
`hub.edevs.tech/`:

- `hub.edevs.tech/design/baseline/*.dc.html` — the team's own **approved HTML visual baseline**
  (explicitly the canonical design source per `SPEC-HUB-0007`, section 3: *"Утверждённые
  дизайн-файлы размещаются только в едином каноническом каталоге:
  `code/hub.edevs.tech/design/baseline/`"*). ~35 screens covering Command Center, Sales
  (overview/clients/dialogs/orders), Departments, Employees, Products, AI agents (list/create/
  detail/knowledge), Integrations, Settings, Auth, the Web Chat widget, and the Checkout flow.
- `hub.edevs.tech/design/baseline/uploads/ADR-HUB-0013-Internal-UI-Design-System.md` — the
  Internal Hub UI design-system decision record (Ant Design + Ant Design X + "Edevs Hub Theme").
- `hub.edevs.tech/design/baseline/uploads/SPEC-HUB-0007-Checkout-UI.md` — the public checkout
  interface spec (`pay.hub.edevs.tech`).
- `hub.edevs.tech/design/baseline/uploads/SPEC-HUB-0003-Web-Chat.md`,
  `SPEC-HUB-0004-Internal-Hub-UI.md`, `SPEC-HUB-0005-Implemented-Internal-UI-Baseline.md`,
  `SPEC-HUB-0001-First-Iteration.md`, `ADR-HUB-0017-AI-Agent-Configuration-UX.md` — supporting
  specs referenced but not individually quoted below.
- `hub.edevs.tech/packages/ui/src/theme.ts` — the actual Ant Design `ThemeConfig` ("Edevs Hub
  Theme") used by the Internal UI: primary color, radii, per-component overrides.
  `hub.edevs.tech/apps/internal-ui/src/styles/base.css` — global resets.
- `hub.edevs.tech/apps/internal-ui/public/favicon.svg` — the one brand mark present in the repo.
- `hub.edevs.tech/content/ai-content-company-filled.md` — the AI agent's system/persona prompts
  for the main company site, used for the Content Fundamentals section below.
- `hub.edevs.tech/apps/checkout` and `hub.edevs.tech/apps/web-chat` — app shells for the public
  surfaces (the checkout app has no implementation yet; the design baseline is ground truth for
  both).

No Figma file or link was provided for this project — the HTML baseline above is the sole
design source, and per the team's own spec it *is* the canonical one.

## Products in scope

1. **Internal Hub** (`hub.edevs.tech`, `apps/internal-ui`) — the OWNER/OPERATOR back office:
   Command Center, Departments, Employees, Products, Sales workspace (overview, clients,
   dialogs, orders), AI agents & knowledge, Integrations, Settings, Auth. Built on Ant Design +
   Ant Design X, desktop-first (1024px+, designed for 1440px).
2. **Web Chat** (`apps/web-chat`) — the embeddable public support/sales chat widget for
   products like FoxRay, handling AI, human handoff, and inline checkout cards.
3. **Checkout** (`apps/checkout`, `pay.hub.edevs.tech`) — the public, mobile-first purchase flow
   that hands off to Bank Tochka for payment and separately tracks payment vs. product delivery.

## Index

- `styles.css` — root stylesheet, imports everything under `tokens/`.
- `tokens/colors.css`, `typography.css`, `spacing.css`, `effects.css` — design tokens.
- `assets/logo-mark.svg`, `favicon.svg` — the one brand mark found in the codebase.
- `components/core/` — Button, IconButton, Input, Checkbox, Tag, Avatar, Icon (intentional
  additions — see below).
- `components/status/` — AttentionStatus, ActorBadge, ChannelBadge.
- `components/cards/` — MetricCard, DepartmentCard, IntegrationHealthCard,
  ProductAIReleaseCard, CommerceStatusTimeline.
- `components/inbox/` — ConversationInbox, KnowledgeDocumentEditor.
- `guidelines/` — foundation specimen cards (Colors, Type, Spacing, Brand).
- `ui_kits/internal-hub/` — Auth → Command Center → Sales · Clients, clickable.
- `ui_kits/web-chat/` — the embeddable chat widget, all 5 states.
- `ui_kits/checkout/` — the public checkout flow, all 8 states.

## Components

Full list (16), grouped by directory:

- **Core** (intentional additions, see below): `Button`, `IconButton`, `Input`, `Checkbox`,
  `Tag`, `Avatar`, `Icon`.
- **Status** (from ADR-HUB-0013's local-component list): `AttentionStatus`, `ActorBadge`,
  `ChannelBadge`.
- **Cards** (from ADR-HUB-0013): `MetricCard`, `DepartmentCard`, `IntegrationHealthCard`,
  `ProductAIReleaseCard`, `CommerceStatusTimeline`.
- **Inbox** (from ADR-HUB-0013): `ConversationInbox`, `KnowledgeDocumentEditor`.

### Intentional additions

ADR-HUB-0013 states the Internal Hub is built on **Ant Design + Ant Design X**, with only ten
named local composite components on top (listed under "Status/Cards/Inbox" above — built
exactly as named). Ant Design itself isn't installable in this static-HTML environment, so to
make the UI kits and composite components actually renderable, this system also includes a
small set of Ant-Design-styled primitives that the ADR assumes but doesn't name:
`Button`, `IconButton`, `Input`, `Checkbox`, `Tag`, `Avatar`, `Icon`. Their visuals (radii,
heights, colors) are copied exactly from the approved HTML baseline, not invented — treat them
as a faithful stand-in for the real Ant Design instance, not a design decision of their own.

## Content fundamentals

Drawn from the AI agent system prompts (`content/ai-content-company-filled.md`) and the copy
throughout the baseline screens (Russian-language product, primary audience is Russian).

- **Language & register:** Russian, informal-but-respectful "вы" register — direct, calm,
  no hard-sell. The agent prompt is explicit: "Пиши как нормальный человек в мессенджере. Не как объявление, не как пресс-релиз и не как робот, который сразу вываливает всю информацию."
- **Tone:** short, human paragraphs, answer the actual question first, then suggest a next
  step: "Отвечай по сути вопроса, короткими живыми абзацами." and "Не дави на покупку. Главная задача общего агента — правильно понять потребность и направить человека туда, где он быстрее получит пользу."
- **Formatting discipline:** no markdown inside chat replies — "Не используй markdown-разметку внутри ответа: не ставь заголовки, списки с маркерами, жирный текст, таблицы и разделители." UI copy elsewhere (Hub, checkout) mirrors this: plain sentences, no bullet-heavy microcopy.
- **Emoji:** rare and situational, never decorative — "Уместные смайлики допустимы, но редко и по ситуации." No emoji appear anywhere in the Hub, Web Chat or Checkout baseline screens.
- **Cultural register:** "Учитывай российский контекст общения: уважительно, прямо, без давления и без чрезмерной рекламности."
- **Honesty/scope discipline:** never invent facts, prices, or promises outside the knowledge
  base — "Если данных не хватает, не выдумывай. Скажи, что этот момент лучше уточнить у специалиста, и передай оператору." and pricing/legal specifics always come from the server, never the client: see Checkout spec §16 ("не доверять цене и составу из состояния браузера").
- **Handoff phrasing:** warm, not robotic, when passing to a human — "При передаче не отвечай сухо. Напиши по-человечески: понял задачу, здесь лучше подключить специалиста, передаю вопрос."
- **UI microcopy style (from the baseline):** short declarative status lines ("Готовим оплату",
  "Оплата получена", "Требует внимания"), technical IDs always in monospace, money always as
  `₽95 040` (₽ prefix, space thousands separator, no decimals for round sums).
- **Domains:** only `edevs.tech` is the confirmed public site; `edevs.ru` is explicitly
  forbidden in agent replies.

## Visual foundations

- **Overall direction (ADR-HUB-0013):** *"светлая тема; премиальный минимализм; высокая, но
  контролируемая информационная плотность; спокойная нейтральная основа; один основной
  акцентный цвет; цвет используется прежде всего для статусов и действий; минимум декоративных
  элементов; отсутствие градиентов, стекломорфизма, неоновых эффектов и визуального шума;
  desktop-first."* (light theme, premium minimalism, one accent color, color reserved for
  status/action, no gradients/glassmorphism/neon, desktop-first for the internal Hub).
- **Color:** one accent, `#1677ff` (Ant Design blue-6) with a `#0958d9` hover/active shade.
  Semantic tokens are mandatory and separate from the accent: success/warning/error/info, plus
  two Hub-specific roles — `ai` (purple, `#722ed1`) vs `human` (blue, same as primary) — and a
  `channel-*` family (MAX purple, Telegram blue, Web Chat teal) used sparingly so multi-channel
  screens don't turn into "a colorful mosaic" (ADR wording). Status color is never the sole
  signal — always paired with text and, in tables, an icon or label.
- **Type:** system font stack only — no bespoke webfont is loaded
  (`-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif`).
  Technical identifiers (order/release/event IDs, emails, obscured phone numbers) switch to a
  monospace stack. Headings use tight letter-spacing (−0.01 to −0.02em); table headers use wide
  spacing (+0.03 to +0.06em) with all-caps and a muted gray.
  Sizes are exact pixel values pulled from the baseline (26/24/20/18/16/14.5/13.5/13/12.5/12/
  11/10.5px) — not snapped to a 4/8 grid.
- **Spacing / density:** "compact enterprise" density is an explicit rule — *"большие пустые
  поля и oversized-карточки запрещены"*. Padding values are odd/precise (9px, 11px, 13px, 14px,
  18px…), not rounded. Control heights: 30/34/36/42/44/48px; topbar is a fixed 56px.
- **Backgrounds:** flat solid colors only. Page background `#f0f2f5`, card surfaces pure white.
  No photography, no illustrations, no repeating patterns/textures, no gradients anywhere
  (buttons, cards, banners are all flat fills). The one "textured" pattern in the system is the
  1px-gap metric grid (white cells on a `#f0f0f0` background, forming hairline dividers) — see
  the Spacing → "Metric Grid In Use" card.
- **Corners:** 7–9px on controls/inputs, 8–9px on buttons, 10–14px on cards/modals, full pill
  on chips/segmented controls, circle on avatars.
- **Cards:** white surface, 1px `#f0f0f0` border, soft shadow (`0 1px 3px rgba(0,0,0,.04)`),
  12px radius as the default; no colored left-border accent except the Command Center's status
  banner (a deliberate, singular exception tied to company health, not a general card pattern).
- **Shadows:** shallow and near-neutral throughout — hairline (`0 1px 2px rgba(0,0,0,.03)`),
  card (`0 1px 3px rgba(0,0,0,.04)`), modal (`0 2px 12px rgba(0,0,0,.05)`), dropdown
  (`0 6px 20px rgba(0,0,0,.12)`). The one colored shadow is the primary button's blue-tinted
  `0 1px 2px rgba(22,119,255,.3)`, used to make the single CTA per screen pop slightly.
- **Animation:** minimal and functional only — a 3-dot typing indicator (`hub-typing`, opacity/
  translateY loop), a spinner (`hub-spin`, rotate) for loading states, and a slow opacity pulse
  (`hub-pulse`) for "in progress" states (e.g. delivering a purchased product). No entrance
  animations, bounces, or parallax anywhere in the baseline.
- **Hover states:** buttons/links darken (primary `#1677ff → #0958d9`); neutral surfaces get a
  light gray fill (`transparent → #f5f5f5`) on hover; secondary buttons swap border+text to the
  accent color on hover. No lightening-on-hover pattern is used.
  **Press/active states:** not distinctly styled in the baseline (no scale/shrink pattern
  observed) — treat hover as the primary interactive affordance; focus-visible gets a solid
  2px accent outline (see `apps/internal-ui/src/styles/base.css`).
  **Disabled:** 55% opacity + `cursor: not-allowed`.
  **Focus:** border-color changes to the accent (inputs) or a visible 2px outline (buttons) —
  never a glow/box-shadow ring.
- **Borders:** hairline `#f0f0f0` almost everywhere (card edges, table row dividers, header
  separators); slightly stronger `#d9d9d9`/`#e8e8e8` on interactive control outlines
  (buttons, inputs) so they read as tappable against the flat background.
- **Transparency & blur:** no blur/glassmorphism anywhere. The only translucent surfaces are
  the Web Chat header's icon buttons (`rgba(255,255,255,0.14–0.26)` over the solid blue header)
  and a full-viewport `position:fixed` transparent scrim used to close open dropdowns/menus.
- **Imagery:** none — the product is data/status-dense enterprise software and transactional
  flows, not marketing pages. No photography, no hand-drawn illustrations, no generic stock
  imagery anywhere in the baseline; nothing to copy in for that reason.
- **Layout rules:** Internal Hub is a fixed sidebar (≈248px) + topbar (56px) + scrollable
  content shell, min-width 1024–1180px depending on screen, content capped at 1200–1340px and
  centered. Web Chat and Checkout are separate, chrome-free, mobile-first single-column flows
  with no sidebar/topbar — explicitly not governed by the Internal Hub's layout rules
  (SPEC-HUB-0007 §4).

## Iconography

- **System:** hand-authored inline SVG, Feather/Lucide-style stroke icons (round caps/joins,
  1.7–2.2px stroke, 24×24 viewBox) — every baseline screen inlines its own `<svg>` rather than
  referencing a shared font or sprite sheet, so there is no icon font or `.svg` sprite file in
  the repo to copy wholesale. This design system's `Icon` component (`components/core/Icon.jsx`)
  collects the ~35 recurring glyphs actually used across the baseline (nav icons, status icons,
  form icons, payment icons) into one reusable primitive with the *exact* path data copied from
  the source screens — nothing was redrawn from imagination.
- **Emoji:** never used anywhere in the product UI (only "rarely, situationally" in AI chat
  replies per the content guidelines above).
  **Unicode-as-icon:** limited to pagination chevrons (`‹ › …`) in table footers.
- **Color:** icons are almost always `currentColor`/neutral gray (`#8c8c8c`/`#595959`), tinted
  to the semantic/accent color only when they sit inside a status chip or colored icon tile
  (e.g. a purple AI bolt icon on a light-purple tile).

## Caveats & where I need your help

1. **No Figma was attached** — everything above comes from the approved HTML baseline in
   `design/baseline/`, which the team's own spec names as canonical. If a Figma file exists,
   attach it and I can cross-check/tighten values.
2. **No FoxRay/FirePage brand assets** — this system only covers Edevs Hub (the internal
   platform + its two public surfaces). FoxRay/Foxray and FirePage are referenced only as
   *product tags* inside Hub (colored labels, no logos). If you want their actual product UI
   or marks in this system, please attach their codebases/design files.
3. **No logo beyond the one favicon mark** — I did not draw one. If Edevs has a real wordmark
   or icon set beyond `favicon.svg`, please attach it and I'll swap it in everywhere.
4. **Ant Design isn't literally bundled** — see "Intentional additions" above; I built
   faithful lightweight stand-ins instead of pulling in the real library, since only static
   HTML/JS/CSS work in this environment.
5. **Internal Hub UI kit covers 2 of many screens** (Command Center + Sales · Clients, behind a
   working Auth gate) rather than all ~35 baseline screens — tell me which screens matter most
   (Departments, AI agents, Orders, Settings…) and I'll extend the kit.

**Ask:** tell me which of the ~35 baseline screens to turn into additional UI-kit pages next,
and whether the Ant-Design-styled primitives above should stay as lightweight stand-ins or be
swapped for real `antd` components if this ever moves into a real build environment.
