import { LOADER_DURATION, LOADER_PATH, LOADER_VALUES } from "./loaderFrames";
import "./loader.css";

// Общий прелоадер продукта (файл владельца, 2026-09-07): капля делится надвое
// и сливается обратно — морфинг одного контура через SMIL. Цвет — currentColor,
// поэтому загрузчик берёт цвет своей темы у контейнера. Ставится везде вместо
// текста «Загрузка…» и самодельных крутилок.
export function Loader({ size = 28, className = "" }: { size?: number; className?: string }) {
  return (
    <svg
      className={`cb-loader ${className}`.trim()}
      viewBox="0 0 100 100"
      width={size}
      height={size}
      fill="currentColor"
      role="status"
      aria-label="Загрузка"
    >
      <path d={LOADER_PATH}>
        <animate
          attributeName="d"
          dur={LOADER_DURATION}
          repeatCount="indefinite"
          calcMode="linear"
          values={LOADER_VALUES}
        />
      </path>
    </svg>
  );
}
