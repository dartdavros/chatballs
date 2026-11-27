import { useState } from "react";
import { ConfigProvider, theme } from "antd";
import type { SiteFields, WebConfig } from "./api";
import { BotAvatar } from "./BotIcon";
import { ConsentText } from "./ConsentText";
import { PreChatField } from "./PreChatField";
import { formPayload, inputValue, preChatFields, validField } from "./preChatModel";
import { t } from "./i18n";
import { widgetClasses as classes } from "./widgetClasses";

export function PreChatForm({ config, accent, title, siteValues, starting, onAccept }: {
  config: WebConfig;
  accent: string;
  title: string;
  siteValues: SiteFields;
  starting: boolean;
  onAccept: (fields: SiteFields) => Promise<void>;
}) {
  const fields = preChatFields(config);
  const [edits, setEdits] = useState<Record<string, string | boolean>>({});
  const values = Object.fromEntries(fields.map((field) => [field.key,
    Object.hasOwn(edits, field.key) ? edits[field.key] : inputValue(field, siteValues[field.key]),
  ]));
  const valid = fields.every((field) => validField(field, values[field.key]));

  return (
    <ConfigProvider theme={{ algorithm: config.appearance?.theme === "dark" ? theme.darkAlgorithm : theme.defaultAlgorithm, token: { colorPrimary: accent } }}>
      <form className={classes.preChat} noValidate onSubmit={(event) => {
        event.preventDefault();
        if (valid && !starting) void onAccept(formPayload(fields, values));
      }}>
        <div className={classes.body}>
          <div className={classes.preChatIntro}>
            {config.autonomous !== false && <BotAvatar size={56} accent={accent} />}
            <h3>{title}</h3>
            {config.preChat?.title && <p>{config.preChat.title}</p>}
          </div>
          <div className={classes.preChatCard}>
            {fields.map((field) => <PreChatField key={field.key} field={field} value={values[field.key]}
              fromSite={Object.hasOwn(siteValues, field.key) && siteValues[field.key] != null && siteValues[field.key] !== ""}
              onChange={(value) => setEdits((previous) => ({ ...previous, [field.key]: value }))} />)}
          </div>
          <ConsentText consent={config.consent} className={classes.preChatConsent} />
        </div>
        <div className={classes.startFooter}>
          <button type="submit" className={classes.startButton} disabled={!valid || starting}>
            {starting ? t("chat.starting") : t("pre_chat.start")}
          </button>
        </div>
      </form>
    </ConfigProvider>
  );
}
