import { useEffect } from "react";

export const PRODUCT_TITLE = "Chatballs";

export function documentTitle(section: string): string {
  return section ? `${section} · ${PRODUCT_TITLE}` : PRODUCT_TITLE;
}

/** Shell владеет заголовком рабочего места; после выхода остаётся название продукта. */
export function useDocumentTitle(section: string): void {
  useEffect(() => {
    document.title = documentTitle(section);
    return () => { document.title = PRODUCT_TITLE; };
  }, [section]);
}
