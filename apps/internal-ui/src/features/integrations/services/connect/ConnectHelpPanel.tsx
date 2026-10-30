import { Icon } from "../../../../shared/icons";
import type { ServiceHelp } from "../types";

/** Справка адаптера справа от формы: «Как получить ссылку» и инструкция сервиса. */
export function ConnectHelpPanel({ help }: { help: ServiceHelp }) {
  return (
    <aside className="service-connect-help">
      <strong>{help.title}</strong>
      {help.steps.length > 0 && <ol>{help.steps.map((step) => <li key={step}>{step}</li>)}</ol>}
      {help.paragraphs.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}
      {help.link && help.url && (
        <a className="link has-icon" href={help.url} target="_blank" rel="noreferrer">{help.link}<Icon name="external" size={12} strokeWidth={2} /></a>
      )}
    </aside>
  );
}
