import { useCallback, useEffect, type RefObject } from "react";

/**
 * Держит ленту прижатой к последнему сообщению.
 *
 * Лоадер создаёт iframe заранее и прячет его через `display:none`, поэтому при
 * первом рендере у ленты `scrollHeight === 0` и обычный автоскролл ничего не
 * делает — панель открывается с началом истории. Поэтому дополнительно слушаем
 * `edevs-chat-opened` от лоадера и доскроллим уже после показа панели.
 *
 * Возвращает функцию скролла — компонент вызывает её из своего эффекта на
 * приход новых сообщений.
 */
export function useScrollToLatest(bodyRef: RefObject<HTMLDivElement | null>): () => void {
  const scrollToLatest = useCallback(() => {
    const node = bodyRef.current;
    if (node) node.scrollTop = node.scrollHeight;
  }, [bodyRef]);

  useEffect(() => {
    let timer = 0;
    function onParentMessage(event: MessageEvent) {
      const data = event.data as { type?: string } | null;
      if (data?.type !== "edevs-chat-opened") return;
      scrollToLatest();
      // Панель только что получила display:block: если размеры ленты ещё не
      // пересчитаны, повторяем после текущей задачи. Через rAF нельзя — в
      // фоновой вкладке кадры не отрисовываются и колбэк не приходит.
      timer = window.setTimeout(scrollToLatest, 0);
    }
    window.addEventListener("message", onParentMessage);
    return () => {
      window.clearTimeout(timer);
      window.removeEventListener("message", onParentMessage);
    };
  }, [scrollToLatest]);

  return scrollToLatest;
}
