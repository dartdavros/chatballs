import { hasRequestBody } from "./httpMethods";
import { t } from "../../../i18n";
import type { FieldErrors, ServerDraft, ToolParameter } from "./types";

export const placeholders = (url: string): string[] => [...url.matchAll(/\{([^{}]*)\}/g)].map((m) => m[1]);

export function mergeErrors(...groups: FieldErrors[]): FieldErrors {
  const merged: FieldErrors = {};
  for (const group of groups) for (const [field, messages] of Object.entries(group)) {
    merged[field] = [...new Set([...(merged[field] ?? []), ...messages])];
  }
  return merged;
}

export function parameterError(parameter: ToolParameter, parameters: ToolParameter[], index: number, url: string, method: string): string {
  if (!/^[A-Za-z_][A-Za-z0-9_]{0,39}$/.test(parameter.name)
    || parameters.some((p, i) => i !== index && p.name === parameter.name)) return t("servers.parameter_invalid");
  if (parameter.location === "path" && !placeholders(url).includes(parameter.name)) return t("servers.path_missing");
  if (!placeholders(url).includes(parameter.name) && parameter.location === "body" && !hasRequestBody(method)) return t("servers.body_post");
  return "";
}

export function draftErrors(draft: ServerDraft): FieldErrors {
  const errors: FieldErrors = {};
  const add = (field: string, message: string) => { (errors[field] ??= []).push(message); };
  const server = draft.externalServer;
  if (!draft.name.trim()) add("name", t("servers.required"));
  if (!server.url.trim()) add("url", t("servers.required"));
  if (server.type === "http") {
    if (!/^[a-z][a-z0-9_]{0,39}$/.test(server.toolName ?? "")) add("toolName", t("servers.invalid_name"));
    if (!server.description.trim()) add("description", t("servers.required"));
    for (const name of new Set(placeholders(server.url))) {
      if (!(server.parameters ?? []).some((p) => p.name === name)) add("url", t("servers.unknown_placeholder", { name: `{${name}}` }));
    }
    (server.parameters ?? []).forEach((parameter, index) => {
      const error = parameterError(parameter, server.parameters ?? [], index, server.url, server.method ?? "GET");
      if (error) add("parameters", `${parameter.name}: ${error}`);
    });
  }
  return errors;
}
