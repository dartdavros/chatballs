import { useState, type MouseEvent } from "react";

import { t } from "../../i18n";
import { Icon } from "../../shared/icons";
import { Button, SelectMenu } from "../../shared/ui-controls";
import type { TemplateVariable } from "./api";

// «Вставить переменную» в окне шаблона ответа (кадр N5): список приходит из
// серверного каталога, пункт вставляет маркер в позицию курсора. У
// дополнительного поля второй строкой — подключение, которому оно принадлежит.

export function TemplateVariableMenu({ variables, onPick, variant = "link" }: {
  variables: TemplateVariable[];
  onPick: (variable: TemplateVariable) => void;
  variant?: "link" | "secondary";
}) {
  const [open, setOpen] = useState(false);
  const disabled = variables.length === 0;
  // Фокус остаётся в редакторе, чтобы переменная вставилась в позицию курсора.
  const keepSelection = (event: MouseEvent<HTMLButtonElement>) => event.preventDefault();
  return (
    <SelectMenu
      disabled={disabled}
      open={open}
      onOpenChange={setOpen}
      options={variables.map((variable) => ({ value: variable.key, label: variable.label, hint: variable.connectionName }))}
      selected={[]}
      placement="bottomRight"
      onSelect={(key) => {
        const variable = variables.find((item) => item.key === key);
        setOpen(false);
        if (variable) onPick(variable);
      }}
    >
      {variant === "secondary"
        ? <Button className="template-variable-button" variant="secondary" icon="plus"
            disabled={disabled} onMouseDown={keepSelection} aria-haspopup="menu" aria-expanded={open}>
            {t("settings.insert_variable")}
          </Button>
        : <button className="link has-icon" type="button" disabled={disabled} onMouseDown={keepSelection}>
            <Icon name="plus" size={13} strokeWidth={2.2} />{t("settings.insert_variable")}
          </button>}
    </SelectMenu>
  );
}
