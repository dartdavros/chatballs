import { copy, type CopyKey } from './copy';

export const settingsIds = [...Array.from({ length: 20 }, (_, index) => `S${index + 20}`), 'S72', 'S73'];
export const settingsCases = settingsIds.map(id => {
  const title = `case${id}` as CopyKey, description = `description${id}` as CopyKey;
  return { id, titleRu: copy.ru[title], titleEn: copy.en[title],
    descriptionRu: copy.ru[description], descriptionEn: copy.en[description], modal: ['S25', 'S26', 'S37'].includes(id) };
});
