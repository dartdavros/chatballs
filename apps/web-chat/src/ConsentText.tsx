import type { WebConfig } from "./api";
import { widgetClasses as classes } from "./widgetClasses";

export function ConsentText({ consent, className }: {
  consent: WebConfig["consent"];
  className?: string;
}) {
  const style = className ? `${classes.consent} ${className}` : classes.consent;
  return (
    <>
      <div className={style} dangerouslySetInnerHTML={{ __html: consent?.text ?? "" }} />
      {consent?.disclosure && <div className={classes.consent} dangerouslySetInnerHTML={{ __html: consent.disclosure }} />}
    </>
  );
}
