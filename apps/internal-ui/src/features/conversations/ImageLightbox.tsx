import { Modal } from "antd";

import { Icon } from "../../shared/icons";
import { formatSize } from "../ai/knowledge/model";
import { t } from "../../i18n";

// Просмотр фото из ленты: сам снимок по центру на затемнённом фоне, без
// карточки; над ним одна строка — имя, размер, «Скачать» и закрытие.

export function ImageLightbox({ open, url, downloadUrl, name, size, onClose }: { open: boolean; url: string; downloadUrl: string; name: string; size?: number; onClose: () => void }) {
  return (
    <Modal open={open} onCancel={onClose} footer={null} closable={false} centered width="auto" className="image-lightbox" rootClassName="image-lightbox-root" destroyOnHidden>
      <div className="image-lightbox-bar">
        <span className="image-lightbox-name" title={name}>{name}</span>
        {size ? <span className="image-lightbox-size">{formatSize(size)}</span> : null}
        <span className="image-lightbox-spacer" />
        <a className="image-lightbox-action" href={downloadUrl} download={name} title={t("common.download")}><Icon name="download" size={16} /><span>{t("common.download")}</span></a>
        <button className="image-lightbox-action" type="button" aria-label={t("common.close")} title={t("conversations.close_esc")} onClick={onClose}><Icon name="xCircle" size={18} /></button>
      </div>
      <img className="image-lightbox-img" src={url} alt={name} />
    </Modal>
  );
}
