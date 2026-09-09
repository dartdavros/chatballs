// Реестр визуальных тем портала (ADR-CHATBALLS-0044).
//
// Единственный источник правды о наборе тем — файловая система: тема = папка
// themes/<id>/ с manifest.ts и theme.css. Регистрировать тему где-то ещё не
// нужно, бэкенд каталог тем не знает и хранит только идентификатор.

import type {
  PortalThemeManifest,
  PortalThemeScheme,
  PortalThemeSchemeSetting,
} from "./types";
import { t } from "../../../i18n";

export const DEFAULT_PORTAL_THEME_ID = "classic";

const manifestModules = import.meta.glob<{ manifest: PortalThemeManifest }>(
  "./*/manifest.ts",
  { eager: true },
);
// CSS темы грузится лениво: в бандл публичной страницы попадает только
// выбранная тема, экран настроек тянет одни манифесты.
const styleModules = import.meta.glob("./*/theme.css");

function folderOf(path: string): string {
  return path.split("/")[1] ?? "";
}

const byId = new Map<string, PortalThemeManifest>();
for (const [path, module] of Object.entries(manifestModules)) {
  const folder = folderOf(path);
  const { manifest } = module;
  if (!manifest || manifest.id !== folder) continue;
  byId.set(folder, manifest);
}

const loaded = new Set<string>();

export function listPortalThemes(): PortalThemeManifest[] {
  return [...byId.values()].sort((left, right) => {
    if (left.id === DEFAULT_PORTAL_THEME_ID) return -1;
    if (right.id === DEFAULT_PORTAL_THEME_ID) return 1;
    return left.name.localeCompare(right.name, "ru");
  });
}

export function findPortalTheme(id: string): PortalThemeManifest | null {
  return byId.get(id) ?? null;
}

/** Тема портала с деградацией до базовой, если сохранённой темы больше нет. */
export function resolvePortalTheme(id: string): PortalThemeManifest {
  const theme = byId.get(id) ?? byId.get(DEFAULT_PORTAL_THEME_ID);
  if (theme) return theme;
  // Каталог тем пуст только в тесте, который сам себе его подменил.
  return {
    id: DEFAULT_PORTAL_THEME_ID,
    name: t("portals.classic"),
    description: "",
    schemes: ["light"],
    preview: { bg: "#ffffff", ink: "#1f1f1f", accent: "#1f1f1f" },
  };
}

/** Схема, которую тема действительно поддерживает. */
export function resolvePortalScheme(
  theme: PortalThemeManifest,
  setting: PortalThemeSchemeSetting,
  prefersDark: boolean,
): PortalThemeScheme {
  const supported: PortalThemeScheme[] = theme.schemes.length
    ? theme.schemes
    : ["light"];
  const wanted: PortalThemeScheme = setting === "SYSTEM"
    ? (prefersDark ? "dark" : "light")
    : (setting === "DARK" ? "dark" : "light");
  return supported.includes(wanted) ? wanted : supported[0];
}

/** Схемы, доступные пользователю в настройках портала для выбранной темы. */
export function schemeOptions(
  theme: PortalThemeManifest,
): Array<[PortalThemeSchemeSetting, string]> {
  const options: Array<[PortalThemeSchemeSetting, string]> = [];
  if (theme.schemes.includes("light")) options.push(["LIGHT", t("profile.light")]);
  if (theme.schemes.includes("dark")) options.push(["DARK", t("profile.dark")]);
  if (theme.schemes.includes("light") && theme.schemes.includes("dark")) {
    options.push(["SYSTEM", t("profile.match_system")]);
  }
  return options.length ? options : [["LIGHT", t("profile.light")]];
}

export async function loadPortalThemeStyles(id: string): Promise<void> {
  if (loaded.has(id)) return;
  const load = styleModules[`./${id}/theme.css`];
  if (!load) return;
  await load();
  loaded.add(id);
}
