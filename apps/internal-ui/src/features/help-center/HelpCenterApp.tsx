import { useEffect, useMemo, useState } from "react";

import { fetchHelpManifest } from "./api";
import { HelpArticle } from "./HelpArticle";
import { HelpHome } from "./HelpHome";
import type { HelpManifest } from "./types";
import "./styles-layout.css";
import "./styles-home.css";
import "./styles-article.css";
import "./styles-responsive.css";

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

  useEffect(() => {
    if (!route) {
      setFailed(true);
      return;
    }
    fetchHelpManifest()
      .then(setManifest)
      .catch(() => setFailed(true));
  }, [route]);

  if (failed || !route) {
    return (
      <main className="help-fatal">
        <strong>Портал поддержки не найден</strong>
        <span>Проверьте адрес или обратитесь к администратору организации.</span>
      </main>
    );
  }
  if (!manifest) {
    return <main className="help-boot-loading"><i /><i /><i /></main>;
  }
  return route.articleSlug
    ? <HelpArticle manifest={manifest} articleSlug={route.articleSlug} />
    : <HelpHome manifest={manifest} />;
}
