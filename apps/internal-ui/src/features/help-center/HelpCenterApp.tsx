import { useEffect, useMemo, useState } from "react";

import { Loader } from "@chatballs/ui";

import { normalizeLanguage, setCurrentLanguage } from "@chatballs/shared";

import { fetchHelpManifest } from "./api";
import { HelpArticle } from "./HelpArticle";
import { HelpHome } from "./HelpHome";
import { usePortalTheme } from "./themes/usePortalTheme";
import type { HelpManifest } from "./types";
import "./styles-layout.css";
import "./styles-home.css";
import "./styles-article.css";
import "./styles-responsive.css";
import { t } from "../../i18n";

type HelpRoute = {
  articleSlug: string | null;
};

function currentRoute(): HelpRoute | null {
  const normalized = window.location.pathname.replace(/\/+$/, "");
  if (normalized === "") return { articleSlug: null };
  const match = normalized.match(/^\/articles\/([^/]+)$/);
  return match ? { articleSlug: decodeURIComponent(match[1]) } : null;
}

export function HelpCenterApp() {
  const route = useMemo(currentRoute, []);
  const [manifest, setManifest] = useState<HelpManifest | null>(null);
  const [failed, setFailed] = useState(false);
  // Тема применяется до первого кадра контента, иначе портал моргнёт
  // базовым оформлением (SPEC-CHATBALLS-0028 §6).
  const themeReady = usePortalTheme(
    manifest ? manifest.portal.theme : null,
    manifest ? manifest.portal.themeScheme : "LIGHT",
  );

  useEffect(() => {
    if (!route) {
      setFailed(true);
      return;
    }
    fetchHelpManifest()
      .then((loaded) => {
        // Язык портала — язык его материалов: статьи написаны на нём, и
        // навигация вокруг них должна говорить так же. Ставится до
        // setManifest, то есть до первого кадра с текстом: к этому моменту
        // нарисован только лоадер, и подписи не успевают мигнуть чужим
        // языком — та же причина, по которой до контента применяется тема.
        setCurrentLanguage(normalizeLanguage(loaded.portal.defaultLocale));
        setManifest(loaded);
      })
      .catch(() => setFailed(true));
  }, [route]);

  if (failed || !route) {
    return (
      <main className="help-fatal">
        <strong>{t("portals.support_portal_not_found")}</strong>
        <span>{t("portals.check_address_or_ask_organization")}</span>
      </main>
    );
  }
  if (!manifest || !themeReady) {
    return <main className="help-boot-loading"><Loader size={44} /></main>;
  }
  return route.articleSlug
    ? <HelpArticle manifest={manifest} articleSlug={route.articleSlug} />
    : <HelpHome manifest={manifest} />;
}
