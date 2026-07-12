const DATA_BY_VERSION_L = [0, 19, 34, 55, 80, 108, 136];
const EC_BY_VERSION_L = [0, 7, 10, 15, 20, 26, 18];
const BLOCKS_BY_VERSION_L = [0, 1, 1, 1, 1, 1, 2];
const PAD_CODEWORDS = [0xec, 0x11];

type MatrixCell = boolean | null;

export type QrMatrix = {
  modules: boolean[];
  size: number;
};

export function createQrMatrix(text: string): QrMatrix {
  const bytes = Array.from(new TextEncoder().encode(text || "CustoCRM"));
  const version = chooseVersion(bytes.length);
  const size = version * 4 + 17;
  const dataCodewords = encodeData(bytes, version);
  const blocks = splitBlocks(dataCodewords, version);
  const codewords = interleaveBlocks(blocks.map((block) => ({
    data: block,
    ec: reedSolomon(block, EC_BY_VERSION_L[version]),
  })));
  const base = createBaseMatrix(version);
  const best = chooseBestMask(base, codewords);
  return {
    modules: best.flat().map(Boolean),
    size,
  };
}

function chooseVersion(byteLength: number): number {
  for (let version = 1; version < DATA_BY_VERSION_L.length; version += 1) {
    const bitLength = 4 + 8 + (byteLength * 8);
    if (Math.ceil(bitLength / 8) <= DATA_BY_VERSION_L[version]) return version;
  }
  return 6;
}

function encodeData(bytes: number[], version: number): number[] {
  const bitLength = DATA_BY_VERSION_L[version] * 8;
  const bits: number[] = [];
  appendBits(bits, 0b0100, 4);
  appendBits(bits, bytes.length, 8);
  bytes.forEach((byte) => appendBits(bits, byte, 8));
  appendBits(bits, 0, Math.min(4, bitLength - bits.length));
  while (bits.length % 8 !== 0) bits.push(0);
  const data: number[] = [];
  for (let index = 0; index < bits.length; index += 8) {
    data.push(bits.slice(index, index + 8).reduce((value, bit) => (value << 1) | bit, 0));
  }
  let padIndex = 0;
  while (data.length < DATA_BY_VERSION_L[version]) {
    data.push(PAD_CODEWORDS[padIndex % 2]);
    padIndex += 1;
  }
  return data;
}

function appendBits(target: number[], value: number, length: number): void {
  for (let bit = length - 1; bit >= 0; bit -= 1) {
    target.push((value >>> bit) & 1);
  }
}

function splitBlocks(data: number[], version: number): number[][] {
  const blockCount = BLOCKS_BY_VERSION_L[version];
  if (blockCount === 1) return [data];
  const blockLength = DATA_BY_VERSION_L[version] / blockCount;
  return Array.from({ length: blockCount }, (_, index) => data.slice(index * blockLength, (index + 1) * blockLength));
}

function interleaveBlocks(blocks: Array<{ data: number[]; ec: number[] }>): number[] {
  const result: number[] = [];
  const maxData = Math.max(...blocks.map((block) => block.data.length));
  const maxEc = Math.max(...blocks.map((block) => block.ec.length));
  for (let index = 0; index < maxData; index += 1) {
    blocks.forEach((block) => {
      if (index < block.data.length) result.push(block.data[index]);
    });
  }
  for (let index = 0; index < maxEc; index += 1) {
    blocks.forEach((block) => {
      if (index < block.ec.length) result.push(block.ec[index]);
    });
  }
  return result;
}

function reedSolomon(data: number[], degree: number): number[] {
  const generator = rsGenerator(degree);
  const result = [...data, ...Array(degree).fill(0)];
  data.forEach((_, index) => {
    const factor = result[index];
    if (factor === 0) return;
    generator.forEach((coefficient, offset) => {
      result[index + offset] ^= gfMul(coefficient, factor);
    });
  });
  return result.slice(data.length);
}

function rsGenerator(degree: number): number[] {
  let result = [1];
  for (let index = 0; index < degree; index += 1) {
    result = polyMul(result, [1, gfPow(2, index)]);
  }
  return result;
}

function polyMul(left: number[], right: number[]): number[] {
  const result = Array(left.length + right.length - 1).fill(0);
  left.forEach((leftValue, leftIndex) => {
    right.forEach((rightValue, rightIndex) => {
      result[leftIndex + rightIndex] ^= gfMul(leftValue, rightValue);
    });
  });
  return result;
}

function gfPow(value: number, power: number): number {
  let result = 1;
  for (let index = 0; index < power; index += 1) result = gfMul(result, value);
  return result;
}

function gfMul(left: number, right: number): number {
  let result = 0;
  let a = left;
  let b = right;
  while (b > 0) {
    if (b & 1) result ^= a;
    a <<= 1;
    if (a & 0x100) a ^= 0x11d;
    b >>>= 1;
  }
  return result;
}

function createBaseMatrix(version: number): { modules: MatrixCell[][]; reserved: boolean[][] } {
  const size = version * 4 + 17;
  const modules = Array.from({ length: size }, () => Array<MatrixCell>(size).fill(null));
  const reserved = Array.from({ length: size }, () => Array<boolean>(size).fill(false));
  drawFinder(modules, reserved, 0, 0);
  drawFinder(modules, reserved, size - 7, 0);
  drawFinder(modules, reserved, 0, size - 7);
  drawTiming(modules, reserved);
  drawAlignment(modules, reserved, version);
  setFunction(modules, reserved, 8, size - 8, true);
  reserveFormat(reserved);
  return { modules, reserved };
}

function drawFinder(modules: MatrixCell[][], reserved: boolean[][], left: number, top: number): void {
  for (let row = -1; row <= 7; row += 1) {
    for (let col = -1; col <= 7; col += 1) {
      const x = left + col;
      const y = top + row;
      if (!inBounds(modules, x, y)) continue;
      if (row < 0 || row > 6 || col < 0 || col > 6) {
        setFunction(modules, reserved, x, y, false);
      } else {
        const edge = row === 0 || row === 6 || col === 0 || col === 6;
        const center = row >= 2 && row <= 4 && col >= 2 && col <= 4;
        setFunction(modules, reserved, x, y, edge || center);
      }
    }
  }
}

function drawTiming(modules: MatrixCell[][], reserved: boolean[][]): void {
  const size = modules.length;
  for (let index = 8; index < size - 8; index += 1) {
    const active = index % 2 === 0;
    setFunction(modules, reserved, index, 6, active);
    setFunction(modules, reserved, 6, index, active);
  }
}

function drawAlignment(modules: MatrixCell[][], reserved: boolean[][], version: number): void {
  if (version === 1) return;
  const position = version * 4 + 10;
  [[6, position], [position, 6], [position, position]].forEach(([x, y]) => {
    if (reserved[y][x]) return;
    for (let row = -2; row <= 2; row += 1) {
      for (let col = -2; col <= 2; col += 1) {
        const edge = Math.abs(row) === 2 || Math.abs(col) === 2;
        const center = row === 0 && col === 0;
        setFunction(modules, reserved, x + col, y + row, edge || center);
      }
    }
  });
}

function reserveFormat(reserved: boolean[][]): void {
  const size = reserved.length;
  for (let index = 0; index <= 8; index += 1) {
    if (index !== 6) {
      reserved[8][index] = true;
      reserved[index][8] = true;
    }
  }
  for (let index = 0; index < 8; index += 1) {
    reserved[8][size - 1 - index] = true;
    reserved[size - 1 - index][8] = true;
  }
}

function setFunction(modules: MatrixCell[][], reserved: boolean[][], x: number, y: number, active: boolean): void {
  if (!inBounds(modules, x, y)) return;
  modules[y][x] = active;
  reserved[y][x] = true;
}

function inBounds(modules: MatrixCell[][], x: number, y: number): boolean {
  return y >= 0 && y < modules.length && x >= 0 && x < modules.length;
}

function chooseBestMask(base: { modules: MatrixCell[][]; reserved: boolean[][] }, codewords: number[]): boolean[][] {
  let bestMatrix: boolean[][] | null = null;
  let bestPenalty = Number.POSITIVE_INFINITY;
  for (let mask = 0; mask < 8; mask += 1) {
    const modules = base.modules.map((row) => [...row]);
    placeData(modules, base.reserved, codewords, mask);
    drawFormat(modules, mask);
    const matrix = modules.map((row) => row.map(Boolean));
    const penalty = scoreMatrix(matrix);
    if (penalty < bestPenalty) {
      bestPenalty = penalty;
      bestMatrix = matrix;
    }
  }
  return bestMatrix ?? base.modules.map((row) => row.map(Boolean));
}

function placeData(modules: MatrixCell[][], reserved: boolean[][], codewords: number[], mask: number): void {
  const bits = codewords.flatMap((codeword) => Array.from({ length: 8 }, (_, index) => (codeword >>> (7 - index)) & 1));
  const size = modules.length;
  let bitIndex = 0;
  let upward = true;
  for (let right = size - 1; right >= 1; right -= 2) {
    if (right === 6) right -= 1;
    for (let vertical = 0; vertical < size; vertical += 1) {
      const row = upward ? size - 1 - vertical : vertical;
      for (let offset = 0; offset < 2; offset += 1) {
        const col = right - offset;
        if (reserved[row][col]) continue;
        const raw = bitIndex < bits.length ? bits[bitIndex] === 1 : false;
        modules[row][col] = raw !== maskApplies(mask, row, col);
        bitIndex += 1;
      }
    }
    upward = !upward;
  }
}

function maskApplies(mask: number, row: number, col: number): boolean {
  switch (mask) {
    case 0: return (row + col) % 2 === 0;
    case 1: return row % 2 === 0;
    case 2: return col % 3 === 0;
    case 3: return (row + col) % 3 === 0;
    case 4: return (Math.floor(row / 2) + Math.floor(col / 3)) % 2 === 0;
    case 5: return ((row * col) % 2) + ((row * col) % 3) === 0;
    case 6: return (((row * col) % 2) + ((row * col) % 3)) % 2 === 0;
    default: return (((row + col) % 2) + ((row * col) % 3)) % 2 === 0;
  }
}

function drawFormat(modules: MatrixCell[][], mask: number): void {
  const size = modules.length;
  const bits = formatBits(mask);
  const first = [[8, 0], [8, 1], [8, 2], [8, 3], [8, 4], [8, 5], [8, 7], [8, 8], [7, 8], [5, 8], [4, 8], [3, 8], [2, 8], [1, 8], [0, 8]];
  const second = [[size - 1, 8], [size - 2, 8], [size - 3, 8], [size - 4, 8], [size - 5, 8], [size - 6, 8], [size - 7, 8], [8, size - 8], [8, size - 7], [8, size - 6], [8, size - 5], [8, size - 4], [8, size - 3], [8, size - 2], [8, size - 1]];
  first.forEach(([x, y], index) => { modules[y][x] = bits[index]; });
  second.forEach(([x, y], index) => { modules[y][x] = bits[index]; });
}

function formatBits(mask: number): boolean[] {
  let value = (1 << 3) | mask;
  let data = value << 10;
  const generator = 0b10100110111;
  for (let bit = 14; bit >= 10; bit -= 1) {
    if (((data >>> bit) & 1) === 1) data ^= generator << (bit - 10);
  }
  value = (((value << 10) | data) ^ 0b101010000010010) & 0x7fff;
  return Array.from({ length: 15 }, (_, index) => ((value >>> index) & 1) === 1);
}

function scoreMatrix(matrix: boolean[][]): number {
  const size = matrix.length;
  let penalty = 0;
  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      if (x + 1 < size && matrix[y][x] === matrix[y][x + 1]) penalty += 1;
      if (y + 1 < size && matrix[y][x] === matrix[y + 1][x]) penalty += 1;
    }
  }
  return penalty;
}
