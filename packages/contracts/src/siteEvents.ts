export type SiteEventField = { name: string; required: boolean } & (
  { type: "string"; maxLength: number } | { type: "number"; minimum: number; maximum: number } | { type: "boolean" }
);
export type PublicSiteEventRule = { name: string; invitation: string; schema: SiteEventField[] };
export type SiteEventRule = PublicSiteEventRule & { id?: string; scenario: string; active: boolean };
export type SiteEventData = Record<string, string | number | boolean>;
export type SiteEvent = { widgetKey: string; name: string; eventId: string; data: SiteEventData };
export type SiteEventState = "pending" | "running" | "sent" | "suppressed" | "failed";
