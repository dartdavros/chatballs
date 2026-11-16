import assert from 'node:assert/strict';

export const expectedHelpTopics = ['external', 'keys', 'capability', 'bindings', 'processing', 'initiative', 'data', 'webFields', 'templates'];

// Executed only in the actual static file document, without replacing APIs or browser objects.
export function revisionGeometry() {
  const frame = document.querySelector('.ea-screen');
  const visible = node => node && getComputedStyle(node).display !== 'none' && node.getBoundingClientRect().height > 0;
  const headers = [...frame.querySelectorAll('.administration-card > .settings-card-head')].map(head => {
    let next = head.nextElementSibling;
    while (next && !visible(next)) next = next.nextElementSibling;
    return { title: head.textContent.trim(), gap: next ? next.getBoundingClientRect().top - head.getBoundingClientRect().bottom : null };
  });
  const badge = frame.querySelector('.ea-external-feature .external-feature-state > .status-pill');
  const badgeGap = badge?.previousElementSibling ? badge.getBoundingClientRect().top - badge.previousElementSibling.getBoundingClientRect().bottom : null;
  const keyActions = [...frame.querySelectorAll('[data-saved-secret]')].map(field => ({
    direction: field.getAttribute('data-saved-secret'),
    texts: [...field.querySelectorAll('.ea-key-actions button')].map(button => button.textContent.trim()),
    iconCounts: [...field.querySelectorAll('.ea-key-actions button')].map(button => button.querySelectorAll('svg').length),
    dropdowns: field.querySelectorAll('.ant-dropdown-trigger').length,
  }));
  const binding = frame.querySelector('[data-agent-bindings]');
  return { headers, badgeGap, keyActions,
    bindings: binding ? { count: binding.querySelectorAll('[data-binding-row]').length,
      addDisabled: binding.querySelector('[data-binding-add]')?.disabled,
      addHint: binding.querySelector('[data-binding-add-hint]')?.textContent.trim(),
      deleteDisabled: [...binding.querySelectorAll('[data-binding-delete]')].map(button => button.disabled),
      fieldDisabled: [...binding.querySelectorAll('[data-binding-agent] .select-box, [data-binding-external-id] input')].map(input => input.disabled),
    } : null,
  };
}

export function validateRevisionGeometry(geometry, c) {
  if (c.group !== 'settings') return;
  for (const header of geometry.headers) {
    if (header.gap !== null) assert(header.gap >= 17.5, `${c.id} divider gap ${header.gap}: ${header.title}`);
  }
  if (['S38', 'S39', 'S72'].includes(c.id)) assert(geometry.badgeGap >= 11.5, `${c.id} badge gap ${geometry.badgeGap}`);
  if (!['S31', 'S32', 'S36'].includes(c.id)) {
    assert.equal(geometry.bindings?.count, 2, `${c.id}: two initial illustrative bindings`);
    const disabled = ['S34', 'S38', 'S72'].includes(c.id);
    assert.equal(geometry.bindings.addDisabled, true, `${c.id}: both available agents are already bound`);
    assert(geometry.bindings.addHint, `${c.id}: unavailable add action explains why`);
    assert(geometry.bindings.deleteDisabled.every(value => value === disabled), `${c.id}: delete availability`);
    assert(geometry.bindings.fieldDisabled.every(value => value === disabled), `${c.id}: binding fields availability`);
    assert.equal(geometry.keyActions.length, 2, `${c.id}: independent key directions`);
    for (const field of geometry.keyActions) {
      assert.equal(field.dropdowns, 0, `${c.id}: no duplicate key-actions menu`);
      assert.equal(field.texts.length, field.direction === 'incoming' ? 2 : 1, `${c.id}: direct key actions`);
      assert.equal(new Set(field.texts).size, field.texts.length, `${c.id}: duplicated key action`);
      assert(field.texts.every(text => text && !/^(действия|actions)$/i.test(text)), `${c.id}: generic actions button`);
      assert(field.iconCounts.every(count => count === 1), `${c.id}: key action uses a DS icon`);
    }
  }
}

export async function settleModal(page, selector = '.ant-modal:visible') {
  const modal = page.locator(selector);
  await modal.waitFor({ state: 'visible' });
  await page.evaluate(async () => {
    const finite = document.getAnimations().filter(animation => animation.effect?.target instanceof Element
      && animation.effect.target.closest('.ant-modal-root') && animation.effect.getTiming().iterations !== Infinity);
    await Promise.all(finite.map(animation => animation.finished.catch(() => {})));
  });
  await page.waitForFunction(() => [...document.querySelectorAll('.ant-modal')].some(element => {
    const style = getComputedStyle(element), rect = element.getBoundingClientRect();
    const transform = new DOMMatrix(style.transform === 'none' ? undefined : style.transform);
    return rect.height && Number(style.opacity) === 1 && Math.abs(transform.a - 1) < .001 && Math.abs(transform.d - 1) < .001;
  }));
  const bounds = await modal.boundingBox(), viewport = page.viewportSize();
  assert(bounds && bounds.x >= -1 && bounds.x + bounds.width <= viewport.width + 1, 'Dialog fits the current viewport');
  return modal;
}

async function closeHelp(page) {
  await page.keyboard.press('Escape');
  await page.locator('.external-help-modal:visible').waitFor({ state: 'hidden' });
}

async function assertPreparedPreview(page, modal, template) {
  const preview = modal.locator(`[data-message-preview="${template}"]`);
  assert.equal(await preview.count(), 1, `Specific ${template} message preview`);
  const frame = preview.locator('.prepared-message-frame');
  await frame.waitFor({ state: 'visible' });
  await page.waitForFunction(name => [...document.querySelectorAll(`.external-help-modal [data-message-preview="${name}"] .prepared-message-frame`)]
    .some(element => element.getBoundingClientRect().height > 20), template, { timeout: 10000 });
  const srcDoc = await frame.getAttribute('srcdoc');
  assert(srcDoc && !/<script\b/i.test(srcDoc), 'Prepared message must be scriptless');
  if (template === 'order') assert(srcDoc.includes('1042'), 'Order preview contains the order example');
  else { assert(/Здравствуйте|Hello/.test(srcDoc), 'Greeting preview contains the greeting'); assert(!srcDoc.includes('1042')); }
}

export async function checkHelpTriggers(page, capture, requiredTopics = []) {
  const topics = await page.locator('[data-help-topic]').evaluateAll(nodes => nodes.map(node => node.getAttribute('data-help-topic')));
  assert(topics.length > 0, 'At least one contextual help trigger is present');
  for (const topic of requiredTopics) assert(topics.includes(topic), `Missing help topic ${topic}`);
  const inspected = [];
  for (let index = 0; index < topics.length; index += 1) {
    const trigger = page.locator('[data-help-topic]').nth(index), topic = topics[index];
    assert.equal(await trigger.getAttribute('aria-haspopup'), 'dialog');
    await trigger.click();
    const modal = await settleModal(page, '.external-help-modal:visible');
    assert((await modal.locator('.ant-modal-title').innerText()).trim(), `${topic}: help title`);
    assert((await modal.locator('.agent-create-lead').innerText()).trim(), `${topic}: explanatory text`);
    if (topic === 'templates') { await assertPreparedPreview(page, modal, 'order'); if (capture) await capture('help-templates'); }
    await closeHelp(page);
    if (capture && ['bindings', 'initiative', 'templates'].includes(topic)) await capture(`section-${topic}`);
    inspected.push(topic);
  }
  return { topics: inspected, closedWithEscape: inspected.length };
}

export async function checkTemplateLinks(page, capture) {
  const links = page.locator('[data-open-message]');
  assert.equal(await links.count(), 2, 'Greeting and order each have a message preview link');
  const inspected = [];
  for (const template of ['greeting', 'order']) {
    const link = page.locator(`[data-open-message="${template}"]`);
    const placement = await link.evaluate(button => {
      const name = button.closest('.service-preset')?.querySelector('strong');
      return name ? button.getBoundingClientRect().top - name.getBoundingClientRect().bottom : null;
    });
    assert(placement !== null && placement >= -1, `${template}: message link must be under its template name`);
    await link.click(); const modal = await settleModal(page, '.external-help-modal:visible');
    await assertPreparedPreview(page, modal, template); if (capture) await capture(`message-${template}`);
    await closeHelp(page); inspected.push(template);
  }
  return { templates: inspected };
}

export async function checkBindings(page, capture) {
  const section = page.locator('[data-agent-bindings]'), rows = section.locator('[data-binding-row]');
  assert.equal(await rows.count(), 2);
  const initialIds = await rows.evaluateAll(nodes => nodes.map(node => node.getAttribute('data-binding-row')));
  const firstAgent = (await rows.first().locator('[data-binding-agent] .select-value').innerText()).trim();
  const secondAgent = (await rows.nth(1).locator('[data-binding-agent] .select-value').innerText()).trim();
  const initialSecondValue = await rows.nth(1).locator('[data-binding-external-id] input').inputValue();
  const snapshot = async () => ({ rows: await rows.evaluateAll(nodes => nodes.map(node => ({
    id: node.getAttribute('data-binding-row'), agent: node.querySelector('[data-binding-agent] .select-value')?.textContent,
    externalId: node.querySelector('[data-binding-external-id] input')?.value,
  }))), save: await page.locator('footer.external-save-footer[data-save-state]').getAttribute('data-save-state') });
  const initial = await snapshot(); assert.equal(initial.save, 'saved');
  assert(await section.locator('[data-binding-add]').isDisabled(), 'All available agents are already bound');
  assert((await section.locator('[data-binding-add-hint]').innerText()).trim(), 'Add action explains the catalogue limit');
  const openRemove = async () => {
    await section.locator(`[data-binding-row="${initialIds[0]}"] [data-binding-delete]`).click();
    const modal = await settleModal(page, '.binding-remove-modal:visible');
    assert((await modal.innerText()).includes(firstAgent), 'Removal identifies the selected existing agent');
    assert.equal(await modal.locator('.decision-dialog-icon svg').count(), 1);
    assert((await modal.getAttribute('class')).includes('is-danger')); return modal;
  };
  let modal = await openRemove(); assert.deepEqual(await snapshot(), initial, 'Opening removal does not change data or dirty state');
  if (capture) await capture('binding-remove-modal');
  await modal.locator('[data-binding-remove-cancel]').click(); await page.locator('.binding-remove-modal:visible').waitFor({ state: 'hidden' });
  assert.deepEqual(await snapshot(), initial, 'Cancel preserves the existing binding');
  await openRemove(); await page.keyboard.press('Escape'); await page.locator('.binding-remove-modal:visible').waitFor({ state: 'hidden' });
  assert.deepEqual(await snapshot(), initial, 'Escape preserves the existing binding');
  modal = await openRemove(); await modal.locator('[data-binding-remove-confirm]').click();
  await page.locator('.binding-remove-modal:visible').waitFor({ state: 'hidden' }); assert.equal(await rows.count(), 1);
  assert.equal(await page.locator('footer.external-save-footer').getAttribute('data-save-state'), 'unsaved');
  assert(await section.locator('[data-binding-add]').isEnabled(), 'Deleting an existing binding makes its agent available');
  const afterDelete = await snapshot();
  const openAdd = async () => {
    await section.locator('[data-binding-add]').click();
    const dialog = await settleModal(page, '.binding-add-modal:visible');
    assert.deepEqual(await snapshot(), afterDelete, 'Opening add never inserts an inline row');
    assert.equal(await dialog.locator('[data-binding-draft-external-id] input').inputValue(), '');
    assert(await dialog.locator('[data-binding-add-confirm]').isDisabled(), 'Blank draft cannot be submitted');
    return dialog;
  };
  const chooseAvailable = async dialog => {
    await dialog.locator('[data-binding-draft-agent] .select-box').click();
    const menu = page.locator('.ant-dropdown.app-dropdown.is-field:visible'); await menu.waitFor({ state: 'visible' });
    const options = (await menu.locator('button').allTextContents()).map(value => value.trim());
    assert.equal(options.length, 2); assert(options.includes(firstAgent)); assert(!options.includes(secondAgent), 'Already-bound agents are excluded');
    await menu.getByRole('button', { name: firstAgent, exact: true }).click(); await menu.waitFor({ state: 'hidden' });
  };
  modal = await openAdd(); await chooseAvailable(modal);
  await modal.locator('[data-binding-draft-external-id] input').fill('   ');
  assert(await modal.locator('[data-binding-add-confirm]').isDisabled(), 'Whitespace-only identifier is invalid');
  if (capture) await capture('binding-add-modal');
  await modal.locator('[data-binding-add-cancel]').click(); await page.locator('.binding-add-modal:visible').waitFor({ state: 'hidden' });
  assert.deepEqual(await snapshot(), afterDelete, 'Cancel discards the add draft');
  modal = await openAdd(); await modal.locator('.ant-modal-close').click(); await page.locator('.binding-add-modal:visible').waitFor({ state: 'hidden' });
  assert.deepEqual(await snapshot(), afterDelete, 'Closing discards the add draft');
  await openAdd(); await page.keyboard.press('Escape'); await page.locator('.binding-add-modal:visible').waitFor({ state: 'hidden' });
  assert.deepEqual(await snapshot(), afterDelete, 'Escape discards the add draft');
  modal = await openAdd();
  await modal.locator('[data-binding-draft-external-id] input').fill('design-binding-example');
  assert(await modal.locator('[data-binding-add-confirm]').isDisabled(), 'An identifier without an agent is invalid');
  await chooseAvailable(modal); await modal.locator('[data-binding-draft-external-id] input').fill('  design-binding-example  ');
  assert(await modal.locator('[data-binding-add-confirm]').isEnabled()); assert.deepEqual(await snapshot(), afterDelete);
  if (capture) await capture('binding-add-valid-modal');
  await modal.locator('[data-binding-add-confirm]').click(); await page.locator('.binding-add-modal:visible').waitFor({ state: 'hidden' });
  assert.equal(await rows.count(), 2); const added = rows.last();
  assert.equal((await added.locator('[data-binding-agent] .select-value').innerText()).trim(), firstAgent);
  assert.equal(await added.locator('[data-binding-external-id] input').inputValue(), 'design-binding-example', 'Added ID is trimmed');
  assert.equal(await added.getAttribute('data-binding-empty'), 'false');
  assert(await section.locator('[data-binding-add]').isDisabled(), 'No duplicate binding is offered');
  assert.equal(await section.locator(`[data-binding-row="${initialIds[1]}"] [data-binding-external-id] input`).inputValue(), initialSecondValue);
  return { initial: 2, deleteConfirmationRequired: true, cancelEscapeAndClosePreserved: true,
    noInlineAdd: true, blankWhitespaceAndMissingAgentBlocked: true, duplicateAgentsExcluded: true,
    afterConfirmedDelete: 1, afterValidModalSubmit: 2, trimmedIdentifier: true };
}
