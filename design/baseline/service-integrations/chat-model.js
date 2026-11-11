// Общие данные и построители состояний для макетов (тема, иконки, статусы, редактор, передача).
// Тема и токены — из «Чат сотрудника Baseline» / «Настройки Baseline»; иконки — shared/icons.tsx.
(function () {
  const theme = (dark, accent) => {
    const T = dark
      ? { canvas: "#101113", surface: "#1b1c1f", surface2: "#181a1d", feed: "#15161a", n1: "#d6d7db", n2: "#c3c5ca", n3: "#9a9ca3", n4: "#767881", n5: "#5b5d66", n6: "#45474f", n7: "#37393f", n8: "#2d2f35", n9: "#27292e", n10: "#212327", ai: "#a98be0", warnText: "#d9a441", okText: "#5fbf7a", errText: "#d9736f", accentText: `color-mix(in srgb,${accent} 62%,white)`, accentHover: `color-mix(in srgb,${accent} 92%,white)`, accentBgPct: 16, tintPct: 12, accentMuted: `color-mix(in srgb,${accent} 84%,#1b1c1f)` }
      : { canvas: "#e4e6ea", surface: "#ffffff", surface2: "#fafafa", feed: "#f5f6f8", n1: "#1f1f1f", n2: "#262626", n3: "#595959", n4: "#8c8c8c", n5: "#bfbfbf", n6: "#d9d9d9", n7: "#e8e8e8", n8: "#f0f0f0", n9: "#f5f5f5", n10: "#fafafa", ai: "#722ed1", warnText: "#d48806", okText: "#237a3f", errText: "#cf1322", accentText: `color-mix(in srgb,${accent} 82%,black)`, accentHover: `color-mix(in srgb,${accent} 88%,black)`, accentBgPct: 10, tintPct: 11, accentMuted: accent };
    return `--c-canvas:${T.canvas};--c-surface:${T.surface};--c-surface2:${T.surface2};--c-feed:${T.feed};--c-msg-in:${dark ? "#1e2025" : "#ffffff"};--c-n1:${T.n1};--c-n2:${T.n2};--c-n3:${T.n3};--c-n4:${T.n4};--c-n5:${T.n5};--c-n6:${T.n6};--c-n7:${T.n7};--c-n8:${T.n8};--c-n9:${T.n9};--c-n10:${T.n10};--c-ai:${T.ai};--c-accent:${T.accentMuted};--c-accent-text:${T.accentText};--c-accent-hover:${T.accentHover};--c-accent-bg:color-mix(in srgb,${accent} ${T.accentBgPct}%,${T.surface});--c-accent-border:color-mix(in srgb,${accent} 40%,${T.surface});--c-accent-shadow:color-mix(in srgb,${accent} ${dark ? 0 : 30}%,transparent);--c-warn-bg:color-mix(in srgb,#faad14 ${T.tintPct}%,${T.surface});--c-warn-border:color-mix(in srgb,#faad14 ${T.tintPct + 25}%,${T.surface});--c-warn-text:${T.warnText};--c-ok-bg:color-mix(in srgb,#52c41a ${T.tintPct}%,${T.surface});--c-ok-border:color-mix(in srgb,#52c41a ${T.tintPct + 20}%,${T.surface});--c-ok-text:${T.okText};--c-err-bg:color-mix(in srgb,#f5222d ${T.tintPct}%,${T.surface});--c-err-border:color-mix(in srgb,#f5222d 40%,${T.surface});--c-err-text:${T.errText};`;
  };

  const I = {
    message: "M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2Z",
    mail: "M3 7a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2zM3 7l9 6 9-6",
    lock: "M6 10h12a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-6a2 2 0 0 1 2-2zM8 10V7a4 4 0 0 1 8 0v3",
    sparkles: "M12 3l1.8 4.6L18.4 9.4 13.8 11.2 12 15.8 10.2 11.2 5.6 9.4 10.2 7.6zM19 16l.8 2.2L22 19l-2.2.8L19 22l-.8-2.2L16 19l2.2-.8zM5 14l.6 1.6L7.2 16.2 5.6 16.8 5 18.4l-.6-1.6L2.8 16.2l1.6-.6z",
    user: "M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0z",
    team: "M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M13 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0zM23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75",
    transfer: "M17 1l4 4-4 4M3 11V9a4 4 0 0 1 4-4h14M7 23l-4-4 4-4M21 13v2a4 4 0 0 1-4 4H3",
    refresh: "M21 12a9 9 0 1 1-2.6-6.4L21 8M21 3v5h-5",
    check: "M20 6 9 17l-5-5",
    close: "M18 6 6 18M6 6l12 12",
    plus: "M12 5v14M5 12h14",
    clock: "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zM12 6v6l4 2",
    warning: "m21.7 18-8-14a2 2 0 0 0-3.5 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.7-3ZM12 9v4M12 17h.01",
    info: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM12 11v5M12 8v.01",
    errorCircle: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM12 8v4M12 16v.01",
    send: "M22 2 11 13M22 2l-7 20-4-9-9-4Z",
    edit: "M12 20h9M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4z",
    trash: "M4 7h16M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2M6 7l1 13a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1l1-13",
    // Бот из веб-виджета (контурная версия, без моргания)
    robot: "M7 4.6h10a3.4 3.4 0 0 1 3.4 3.4v6.2a3.4 3.4 0 0 1-3.4 3.4h-6.2l-3.4 2.8v-2.8H7A3.4 3.4 0 0 1 3.6 14.2V8A3.4 3.4 0 0 1 7 4.6zM12 4.6V2.9M12 1.4v.01M9 9.4v1.4M15 9.4v1.4M9.2 13.4c.8 1 1.7 1.5 2.8 1.5s2-.5 2.8-1.5M1.6 9.8v2.6M22.4 9.8v2.6",
    text: "M5 5h14M12 5v14M8 19h8",
    globe: "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM2 12h20M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20",
    eye: "M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7-10-7-10-7zM15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0z",
    eyeOff: "m3 3 18 18M10.6 10.6a3 3 0 0 0 3.8 3.8M9.9 4.3A10.6 10.6 0 0 1 12 4c6.5 0 10 8 10 8a18 18 0 0 1-3.1 4.2M6.1 6.1C3.5 7.9 2 12 2 12s3.5 8 10 8c1.4 0 2.7-.3 3.9-.9",
    bell: "M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9M10.3 21a1.94 1.94 0 0 0 3.4 0",
    external: "M7 17 17 7M8 7h9v9",
    undo: "M9 14 4 9l5-5M4 9h11a5 5 0 0 1 0 10h-3",
    shield: "M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z",
    download: "M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3",
    reply: "M9 17 4 12l5-5M20 18v-2a4 4 0 0 0-4-4H4",
    xCircle: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM9 9l6 6M15 9l-6 6",
  };

  // Рабочая доступность (выбирает сотрудник) — квадратная метка; присутствие в приложении — круглая точка на фото.
  // Иконки lucide: circle-check · circle-minus · coffee · moon. dot — фон для метки (data-URI), hex — цвет.
  const LUCIDE = {
    ready: "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zM9 12l2 2 4-4",
    busy: "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zM8 12h8",
    break: "M10 2v2M14 2v2M6 2v2M16 8a1 1 0 0 1 1 1v8a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4V9a1 1 0 0 1 1-1h14a4 4 0 1 1 0 8h-1",
    off: "M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z",
  };
  const iconBg = (path, hex) => `url("data:image/svg+xml,${encodeURIComponent(`<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='${hex}' stroke-width='2.3' stroke-linecap='round' stroke-linejoin='round'><path d='${path}'/></svg>`)}") center/contain no-repeat`;
  const HEX = { ready: "#52c41a", busy: "#ff4d4f", break: "#faad14", off: "#8c8c8c" };
  const STATUS = {
    ready: { label: "Готов принимать", short: "Готов", color: "var(--c-ok-text)", hex: HEX.ready, icon: LUCIDE.ready, dot: iconBg(LUCIDE.ready, HEX.ready) },
    busy: { label: "Занят", short: "Занят", color: "var(--c-err-text)", hex: HEX.busy, icon: LUCIDE.busy, dot: iconBg(LUCIDE.busy, HEX.busy) },
    break: { label: "Перерыв", short: "Перерыв", color: "var(--c-warn-text)", hex: HEX.break, icon: LUCIDE.break, dot: iconBg(LUCIDE.break, HEX.break) },
    off: { label: "Недоступен", short: "Недоступен", color: "var(--c-n4)", hex: HEX.off, icon: LUCIDE.off, dot: iconBg(LUCIDE.off, HEX.off) },
    unknown: { label: "Статус не загружен", short: "—", color: "var(--c-n4)", dot: "transparent" },
  };
  const pres = (on) => on ? { presBg: "#52c41a", presRing: "none" } : { presBg: "var(--c-surface)", presRing: "inset 0 0 0 1.5px var(--c-n5)" };

  const PEOPLE = {
    ak: { name: "Анна Ким", initials: "", av: "url(assets/av-2.png) center/cover" },
    do: { name: "Дмитрий Орлов", initials: "ДО", av: "#3f7ec2" },
    ek: { name: "Елена Кузнецова", initials: "", av: "url(assets/av-4.png) center/cover" },
    sk: { name: "Сергей Крылов", initials: "", av: "url(assets/av-3.png) center/cover" },
    ot: { name: "Ольга Тимина", initials: "ОТ", av: "#c2703f" },
    pv: { name: "Павел Воронцов-Вельяминов", initials: "ПВ", av: "#7d5ba6" },
  };

  const tab = (key, active, label, icon, o = {}) => ({ key, label, icon, title: o.title || label, line: key === active ? (o.lineColor || "var(--c-accent-text)") : "transparent", color: o.disabled ? "var(--c-n5)" : key === active ? (o.lineColor || "var(--c-accent-text)") : "var(--c-n4)", weight: key === active ? 600 : 500, cursor: o.disabled ? "not-allowed" : "pointer", opacity: o.disabled ? 0.7 : 1 });

  // o: mode reply|email|comment, text, segs, placeholder, draft, ai (idle|busy|off|hidden), send state, foot, menu, hint, emailRows, emailDisabled, channel
  const composer = (o = {}) => {
    const mode = o.mode || "reply";
    const WARN = "var(--c-warn-text)";
    const tabs = [
      tab("reply", mode, "Ответ клиенту", I.message),
      ...(o.noEmail ? [] : [tab("email", mode, "Письмо", I.mail, { disabled: o.emailDisabled, title: o.emailDisabled || "Письмо" })]),
      tab("comment", mode, "Комментарий", I.lock, { lineColor: WARN, title: "Внутренний комментарий — только для сотрудников" }),
    ];
    const aud = mode === "comment"
      ? { audText: "Только сотрудники — клиент не увидит", audColor: WARN, audIcon: I.lock, border: "var(--c-warn-border)", shadow: "0 0 0 3px var(--c-warn-bg)" }
      : mode === "email"
        ? { audText: o.audText || "Письмо клиенту на почту", audColor: "var(--c-accent-text)", audIcon: I.mail, border: "var(--c-n7)", shadow: "0 1px 3px rgba(0,0,0,0.04)" }
        : { audText: o.audText || "Увидит клиент · Web Chat", audColor: "var(--c-accent-text)", audIcon: I.user, border: "var(--c-n7)", shadow: "0 1px 3px rgba(0,0,0,0.04)" };
    const aiState = o.ai || (mode === "reply" ? "idle" : "hidden");
    const ai = aiState === "hidden" ? null : {
      idle: { label: "Черновик AI", title: "Подготовить черновик ответа", bg: "transparent", color: "var(--c-ai)", cursor: "pointer" },
      active: { label: "Черновик AI", title: "Черновик открыт", bg: "color-mix(in srgb,var(--c-ai) 10%,var(--c-surface))", color: "var(--c-ai)", cursor: "pointer" },
      busy: { label: "Готовим…", title: "Черновик готовится", bg: "color-mix(in srgb,var(--c-ai) 10%,var(--c-surface))", color: "var(--c-ai)", cursor: "default" },
      off: { label: "Черновик AI", title: o.aiOffTitle || "Недоступно", bg: "transparent", color: "var(--c-n5)", cursor: "not-allowed" },
    }[aiState];
    const sendLabel = o.sendLabel || (mode === "comment" ? "Добавить комментарий" : mode === "email" ? "Отправить письмо" : "Отправить");
    const sendOff = !!o.sendOff;
    const sendBg = sendOff ? "var(--c-n8)" : mode === "comment" ? "#d48806" : "var(--c-accent)";
    let segs = o.segs || (o.text ? [{ text: o.text }] : []);
    segs = segs.map((s) => s.v ? { text: s.text, bg: s.bad ? "var(--c-err-bg)" : "var(--c-warn-bg)", color: s.bad ? "var(--c-err-text)" : "var(--c-warn-text)", pad: "1px 4px", weight: 600, ring: s.bad ? "inset 0 0 0 1px var(--c-err-border)" : "inset 0 0 0 1px var(--c-warn-border)" } : { text: s.text, bg: "transparent", color: "var(--c-n2)", pad: "0", weight: 400, ring: "none" });
    const placeholder = segs.length ? "" : (o.placeholder || (mode === "comment" ? "Комментарий для коллег… Клиент его не увидит" : mode === "email" ? "Текст письма…" : "Введите сообщение… Shift+Enter — перенос строки, «/» — шаблон ответа"));
    const footTone = { err: ["var(--c-err-text)", "#f5222d"], warn: ["var(--c-warn-text)", "#faad14"], ok: ["var(--c-ok-text)", "#52c41a"], muted: ["var(--c-n4)", "var(--c-n5)"], ai: ["var(--c-ai)", "var(--c-ai)"] }[o.footTone || "muted"];
    return {
      active: !o.locked, locked: !!o.locked, lockedTitle: o.lockedTitle, lockedText: o.lockedText, lockedAction: o.lockedAction || "",
      hint: o.hint || "", hintColor: o.hintColor || "var(--c-n4)", hintDot: o.hintDot || "var(--c-n5)",
      tabs, ...aud, isEmail: mode === "email", emailRows: o.emailRows || [], draft: o.draft || null,
      segs, placeholder, edited: o.edited || "", media: mode === "reply" || mode === "email", voice: mode === "reply", ai,
      tplBg: o.menu ? "var(--c-n9)" : "transparent", tplColor: o.menu ? "var(--c-n2)" : "var(--c-n4)", menu: o.menu || null,
      send: sendLabel, sendBg, sendColor: sendOff ? "var(--c-n5)" : "#fff", sendCursor: sendOff ? "not-allowed" : "pointer", sendTitle: o.sendTitle || sendLabel,
      foot: o.foot || "", footLink: o.footLink || "", footColor: footTone[0], footDot: footTone[1],
    };
  };

  const btn = (label, icon, kind) => kind === "primary"
    ? { label, icon, bg: "var(--c-ai)", color: "#fff", border: "var(--c-ai)" }
    : { label, icon, bg: "var(--c-surface)", color: kind === "danger" ? "var(--c-err-text)" : "var(--c-n2)", border: "var(--c-n7)" };
  const AI_BORDER = "color-mix(in srgb,var(--c-ai) 28%,var(--c-surface))", AI_BG = "color-mix(in srgb,var(--c-ai) 6%,var(--c-surface))";
  const draft = {
    loading: (sub) => ({ title: "Готовим черновик", sub: sub || "по переписке и базе знаний агента", icon: I.sparkles, iconColor: "var(--c-ai)", titleColor: "var(--c-ai)", border: AI_BORDER, bg: AI_BG, loading: true, actions: [btn("Остановить", I.close)], foot: "Клиенту ничего не отправляется", closable: false }),
    ready: (text, alts, idx) => ({ title: "Черновик AI", sub: "проверьте перед отправкой", icon: I.sparkles, iconColor: "var(--c-ai)", titleColor: "var(--c-ai)", border: AI_BORDER, bg: AI_BG, text, closable: true,
      alts: alts > 1 ? Array.from({ length: alts }, (_, i) => ({ label: String(i + 1), title: `Вариант ${i + 1} из ${alts}`, bg: i === idx ? "var(--c-ai)" : "transparent", color: i === idx ? "#fff" : "var(--c-n3)" })) : null,
      actions: [btn("Вставить в ответ", I.check, "primary"), btn("Другая формулировка", I.refresh)], foot: "Отправка — только вручную" }),
    rephrasing: (text, alts) => ({ title: "Черновик AI", sub: "готовим другую формулировку…", icon: I.refresh, iconColor: "var(--c-ai)", titleColor: "var(--c-ai)", border: AI_BORDER, bg: AI_BG, text, closable: true,
      alts: Array.from({ length: alts }, (_, i) => ({ label: String(i + 1), title: `Вариант ${i + 1}`, bg: i === 0 ? "var(--c-ai)" : "transparent", color: i === 0 ? "#fff" : "var(--c-n3)" })).concat([{ label: "…", title: "Готовится", bg: "transparent", color: "var(--c-ai)" }]),
      loading: false, actions: [btn("Вставить в ответ", I.check, "primary")], foot: "Прежний вариант остаётся доступен" }),
    error: (text) => ({ title: "Не удалось подготовить черновик", sub: "", icon: I.errorCircle, iconColor: "var(--c-err-text)", titleColor: "var(--c-err-text)", border: "var(--c-err-border)", bg: "var(--c-err-bg)", text: text || "AI-провайдер не ответил. Попробуйте ещё раз или ответьте вручную.", closable: true, actions: [btn("Повторить", I.refresh)], foot: "" }),
  };

  // Получатели передачи. st: ready|busy|break|off; on: в приложении; allowed: разрешено ли назначение в этом статусе
  const recipient = (pk, st, on, presText, load, o = {}) => {
    const p = PEOPLE[pk], S = STATUS[st];
    const allowed = o.allowed !== false;
    return { ...p, ...pres(on), presenceTitle: on ? "Приложение открыто" : "Приложение закрыто", sub: allowed ? presText : o.reason, subColor: allowed ? "var(--c-n4)" : "var(--c-err-text)", subWs: allowed ? "nowrap" : "normal",
      status: S.label, stColor: S.color, stDot: S.dot, load, loadColor: "var(--c-n3)", opacity: allowed ? 1 : 0.5, on: !!o.on, radio: o.on ? "var(--c-accent)" : "var(--c-n6)",
      bg: o.on ? "var(--c-accent-bg)" : "transparent", hover: allowed ? (o.on ? "var(--c-accent-bg)" : "var(--c-n10)") : "transparent", cursor: allowed ? "pointer" : "not-allowed", title: allowed ? "" : o.reason, head: "" };
  };
  const transfer = (o = {}) => {
    const people = o.people || [
      { head: "МОЖНО НАЗНАЧИТЬ" },
      recipient("ak", "ready", true, "в приложении", "3 диалога", { on: o.sel === "ak" }),
      recipient("do", "busy", true, "в приложении", "6 диалогов", { on: o.sel === "do" }),
      recipient("pv", "ready", false, "не в приложении · 12 мин", "1 диалог", { on: o.sel === "pv" }),
      { head: "НЕЛЬЗЯ НАЗНАЧИТЬ" },
      recipient("sk", "break", true, "", "2 диалога", { allowed: false, reason: "На перерыве — в этом статусе назначать нельзя" }),
      recipient("ot", "off", false, "", "—", { allowed: false, reason: "Недоступна — в этом статусе назначать нельзя" }),
    ];
    const reasonSet = !!o.reason;
    const states = { idle: ["Передать", I.transfer, "var(--c-accent)", "#fff", "pointer"], off: ["Передать", I.transfer, "var(--c-n8)", "var(--c-n5)", "not-allowed"], busy: ["Передаём…", I.refresh, "color-mix(in srgb,var(--c-accent) 70%,var(--c-surface))", "#fff", "default"] }[o.submit || (o.sel && reasonSet ? "idle" : "off")];
    return {
      sub: o.sub || "Марина Белова · Web Chat · ответственная — вы", banner: o.banner || null, bodyOpacity: o.bodyOpacity || 1, listH: o.listH || "250px", people,
      reason: o.reason || "Выберите причину", reasonColor: reasonSet ? "var(--c-n1)" : "var(--c-n5)", reasonBorder: o.reasonErr ? "var(--c-err-border)" : "var(--c-n7)", reasonRing: o.reasonErr ? "0 0 0 3px var(--c-err-bg)" : "none", reasonErr: o.reasonErr || "",
      comment: o.comment || "Например: что уже сделано и что осталось", commentColor: o.comment ? "var(--c-n2)" : "var(--c-n5)",
      footNote: o.footNote || (o.sel ? `Ответственным станет ${PEOPLE[o.sel].name}. Вы потеряете право отвечать, если не останетесь участником.` : "Выберите сотрудника и причину"),
      submit: states[0], submitIcon: states[1], submitBg: states[2], submitColor: states[3], submitCursor: states[4],
    };
  };

  const banner = (tone, title, text, actions) => {
    const T = { err: ["var(--c-err-bg)", "var(--c-err-border)", "var(--c-err-text)", I.errorCircle], warn: ["var(--c-warn-bg)", "var(--c-warn-border)", "var(--c-warn-text)", I.warning], ok: ["var(--c-ok-bg)", "var(--c-ok-border)", "var(--c-ok-text)", I.check], info: ["var(--c-accent-bg)", "var(--c-accent-border)", "var(--c-accent-text)", I.info] }[tone];
    return { bg: T[0], border: T[1], color: T[2], icon: T[3], title, text, actions: actions ? actions.map((a, i) => ({ label: a, bg: i === 0 ? "var(--c-accent)" : "var(--c-surface)", color: i === 0 ? "#fff" : "var(--c-n2)", border: i === 0 ? "var(--c-accent)" : "var(--c-n7)" })) : null };
  };

  window.ChatModel = { theme, I, STATUS, pres, PEOPLE, composer, draft, transfer, recipient, banner };
})();
