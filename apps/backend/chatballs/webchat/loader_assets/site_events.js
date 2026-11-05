  // The early stub uses eventQueue, never the legacy field queue q.
  var eventApi = window.Chatballs;
  var broker = eventApi.__siteEvents;
  if (!broker) {
    broker = eventApi.__siteEvents = { pending: Object.create(null), listeners: Object.create(null), pendingCount: 0 };
    broker.expire = function (key, at) {
      window.setTimeout(function () {
        var packets = broker.pending[key] || [];
        var fresh = packets.filter(function (packet) { return Date.now() - packet.receivedAt < 300000; });
        broker.pendingCount -= packets.length - fresh.length;
        if (fresh.length) broker.pending[key] = fresh;
        else delete broker.pending[key];
      }, Math.max(0, 300000 - (Date.now() - at)));
    };
    var earlyEvents = Array.isArray(eventApi.eventQueue) ? eventApi.eventQueue.slice() : [];
    if (Array.isArray(eventApi.eventQueue)) eventApi.eventQueue.length = 0;
    eventApi.eventQueue = [];
    broker.route = function (event, receivedAt) {
      try {
        if (typeof receivedAt !== "number" || !Number.isFinite(receivedAt) || receivedAt > Date.now() || Date.now() - receivedAt >= 300000) return false;
        if (!event || typeof event.widgetKey !== "string" || !event.widgetKey ||
            typeof event.name !== "string" || typeof event.eventId !== "string" ||
            !event.eventId.trim() || event.eventId.length > 200 || !event.data ||
            typeof event.data !== "object" || Array.isArray(event.data)) return false;
        var encoded = JSON.stringify(event);
        if (new TextEncoder().encode(encoded).length > 20 * 1024) return false;
        var packet = { event: JSON.parse(encoded), receivedAt: receivedAt };
        var listener = broker.listeners[event.widgetKey];
        if (listener) return listener(packet);
        if (broker.pendingCount >= 100) return false;
        (broker.pending[event.widgetKey] = broker.pending[event.widgetKey] || []).push(packet);
        broker.pendingCount += 1;
        broker.expire(event.widgetKey, receivedAt);
        return true;
      } catch (_) { return false; }
    };
    eventApi.emitEvent = function (event) { return broker.route(event, Date.now()); };
    earlyEvents.forEach(function (packet) {
      if (packet) broker.route(packet.event, packet.receivedAt);
    });
    earlyEvents.length = 0;
  }
  var siteEventReady = false, siteEventFocus = false, pendingSiteEvents = broker.pending[widgetKey] || [];
  var siteEventExpiry = null;
  broker.pendingCount -= pendingSiteEvents.length;
  delete broker.pending[widgetKey];
  function expireSiteQueue() {
    window.clearTimeout(siteEventExpiry);
    pendingSiteEvents = pendingSiteEvents.filter(function (packet) { return Date.now() - packet.receivedAt < 300000; });
    if (pendingSiteEvents.length) siteEventExpiry = window.setTimeout(expireSiteQueue,
      Math.max(0, 300000 - (Date.now() - pendingSiteEvents[0].receivedAt)));
  }
  expireSiteQueue();
  function flushSiteEvent() {
    if (!siteEventReady || !pendingSiteEvents.length || !frame || !frame.contentWindow) return;
    var packets = pendingSiteEvents;
    pendingSiteEvents = [];
    window.clearTimeout(siteEventExpiry);
    // The widget alone knows the current schema. It keeps the first matching
    // candidate; an invalid earlier candidate must not hide a valid one.
    packets.forEach(function (packet) {
      if (Date.now() - packet.receivedAt >= 300000) return;
      frame.contentWindow.postMessage({ type: "chatballs-site-event", widgetKey: widgetKey,
        instanceId: instanceId, event: packet.event, receivedAt: packet.receivedAt }, origin);
    });
    packets.length = 0;
  }
  if (widgetKey) broker.listeners[widgetKey] = function (packet) {
    expireSiteQueue();
    if (pendingSiteEvents.length >= 100) return false;
    pendingSiteEvents.push(packet);
    expireSiteQueue();
    flushSiteEvent();
    return true;
  };
  function notifySiteEvent(action) {
    if (!frame || !frame.contentWindow) return;
    frame.contentWindow.postMessage({ type: "chatballs-site-event-control", action: action,
      instanceId: instanceId, widgetKey: widgetKey }, origin);
  }
  function handleSiteEventMessage(data) {
    if (data.instanceId !== instanceId || data.widgetKey !== widgetKey) return;
    if (data.type === "chatballs-site-events-ready") { siteEventReady = true; flushSiteEvent(); }
    if (data.type === "chatballs-site-event-invitation") renderSiteInvitation(data.invitation);
    if (data.type === "chatballs-site-event-open") { siteEventFocus = true; setOpen(true); }
  }
  function focusSiteEventPanel() {
    if (!siteEventFocus) return;
    siteEventFocus = false;
    if (open) notifySiteEvent("focus");
  }
