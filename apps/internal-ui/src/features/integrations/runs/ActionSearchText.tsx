import { actionSearchWords } from "./actionPickerModel";

export function ActionSearchText({ text, search }: { text: string; search: string }) {
  const words = actionSearchWords(search);
  if (!words.length) return <>{text}</>;
  const normalized = text.toLocaleLowerCase().replaceAll("ё", "е");
  const marks = Array.from({ length: text.length }, () => false);
  for (const word of words) {
    for (let start = normalized.indexOf(word); start >= 0; start = normalized.indexOf(word, start + 1)) {
      for (let index = start; index < start + word.length; index++) marks[index] = true;
    }
  }
  const parts: Array<{ text: string; marked: boolean }> = [];
  for (let start = 0; start < text.length;) {
    let end = start + 1;
    while (end < text.length && marks[end] === marks[start]) end++;
    parts.push({ text: text.slice(start, end), marked: marks[start] });
    start = end;
  }
  return <>{parts.map((part, index) => part.marked ? <mark key={index}>{part.text}</mark> : part.text)}</>;
}
