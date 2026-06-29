export function chartPaths(values: number[]) {
  const width = 1000;
  const height = 260;
  const padLeft = 10;
  const padRight = 10;
  const padTop = 18;
  const padBottom = 26;
  const innerWidth = width - padLeft - padRight;
  const innerHeight = height - padTop - padBottom;
  const max = Math.max(...values, 0) * 1.12 || 1;
  const x = (index: number) => padLeft + innerWidth * (values.length === 1 ? 0 : index / (values.length - 1));
  const y = (value: number) => padTop + innerHeight * (1 - value / max);
  const points = values.map((value, index) => ({ x: x(index), y: y(value) }));
  const linePath = `M${points.map((point) => `${point.x.toFixed(1)},${point.y.toFixed(1)}`).join(" L")}`;
  const areaPath = `${linePath} L${x(values.length - 1).toFixed(1)},${(padTop + innerHeight).toFixed(1)} L${padLeft.toFixed(1)},${(padTop + innerHeight).toFixed(1)} Z`;
  return {
    linePath,
    areaPath,
    last: points[points.length - 1],
    gridLines: [padTop + innerHeight * 0.25, padTop + innerHeight * 0.55, padTop + innerHeight * 0.85].map((line) => line.toFixed(1)),
  };
}
