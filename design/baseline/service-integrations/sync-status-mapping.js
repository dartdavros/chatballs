/* Данные для согласованной таблицы статусов; только дизайн-референс. */
(() => {
  const build = (direction, maps = {}, statuses, stages) => {
    const directions = direction === 'both' ? ['out', 'in'] : [direction];
    return directions.map(key => {
      const outgoing = key === 'out';
      const sources = outgoing ? statuses : stages;
      const targets = outgoing ? stages : statuses;
      return {
        key,
        sourceLabel: outgoing ? 'Статус диалога' : 'Стадия',
        targetLabel: outgoing ? 'Стадия' : 'Статус диалога',
        rows: sources.map(([id, label]) => ({
          id,
          label,
          value: maps[key]?.[id] || '',
          options: [['', 'Не менять'], ...targets],
        })),
      };
    });
  };
  globalThis.ServiceSyncStatusMapping = { build };
})();
