import baseCss from "./widget.css?raw";
import preChatCss from "./preChat.css?raw";
import consentCss from "./consent.css?raw";
import dictationCss from "./speech/dictation.css?raw";
import playbackCss from "./speech/playback.css?raw";

/** Both sheets belong to the chat document, never the embedding page. */
export function WidgetStyles({ customCss }: { customCss: string }) {
  return <><style data-cb-styles="base">{baseCss + preChatCss + consentCss + dictationCss + playbackCss}</style><style data-cb-styles="custom">{customCss}</style></>;
}
