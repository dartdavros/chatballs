import { Modal } from "antd";

import { Icon } from "../../shared/icons";
import { formatSize } from "../ai/knowledge/model";

// Просмотр фото из ленты: попап с оригиналом, именем, размером и «Скачать».

export function ImageLightbox({ open, url, downloadUrl, name, size, onClose }: { open: boolean; url: string; downloadUrl: string; name: string; size?: number; onClose: () => void }) {
  return (
    <Modal open={open} onCancel={onClose} footer={null} closable={false} centered width="min(92vw, 1080px)" className="image-lightbox" destroyOnHidden>
      <div className="image-lightbox-head">
        <div className="image-lightbox-meta">
          <strong title={name}>{name}</strong>
          {size ? <small>{formatSize(size)}</small> : null}
        </div>
        <a className="image-lightbox-download" href={downloadUrl} download={name}><Icon name="download" size={15} />Скачать</a>
        <button className="image-lightbox-close" type="button" aria-label="Закрыть" onClick={onClose}><Icon name="xCircle" size={18} /></button>
      </div>
      <div className="image-lightbox-body" onClick={onClose}>
        <img src={url} alt={name} onClick={(event) => event.stopPropagation()} />
      </div>
    </Modal>
  );
}
