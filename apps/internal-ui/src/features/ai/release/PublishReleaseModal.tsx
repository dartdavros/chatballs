import { Icon } from "../../../shared/icons";
import { Button } from "../../../shared/ui-controls";
import type { AiReleaseFull } from "../detail/model";
import { releaseLabel } from "./model";

export function PublishReleaseModal({
  checked,
  close,
  confirm,
  publishing,
  release,
  setChecked,
}: {
  checked: boolean;
  close: () => void;
  confirm: () => void;
  publishing: boolean;
  release: AiReleaseFull;
  setChecked: (checked: boolean) => void;
}) {
  return (
    <div className="release-modal-backdrop">
      <div className="release-modal">
        <div className="release-modal-body">
          <div className="release-modal-title">
            <span><Icon name="warning" size={22} /></span>
            <div>
              <h3>Опубликовать {releaseLabel(release)}?</h3>
              <p>Атомарная публикация конфигурации {release.product.name} Sales</p>
            </div>
          </div>
          <div className="release-modal-warning">
            Новые ответы во <b>всех активных диалогах</b> сразу будут использовать эту версию. Текущая опубликованная версия перейдёт в архив. Уже отправленные ответы не изменятся.
          </div>
          <button className="release-confirm-line" type="button" onClick={() => setChecked(!checked)}>
            <span className={checked ? "release-confirm-box checked" : "release-confirm-box"}>{checked && <Icon name="check" size={12} />}</span>
            <span>Понимаю, что активные диалоги переключатся на новую версию</span>
          </button>
        </div>
        <div className="release-modal-footer">
          <Button variant="secondary" onClick={close}>Отмена</Button>
          <Button variant="primary" icon="send" disabled={!checked || publishing} onClick={confirm}>Опубликовать</Button>
        </div>
      </div>
    </div>
  );
}
