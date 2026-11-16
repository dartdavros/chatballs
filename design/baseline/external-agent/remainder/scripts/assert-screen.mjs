import assert from 'node:assert/strict';
export function validate(g,c,test){
  assert.equal(g.id,c.id);assert.equal(g.width,test.width);assert.equal(g.height,980);
  assert.equal(g.lang,test.lang);assert.equal(g.theme,test.theme);assert.deepEqual(g.overflow,[],`${c.id} ${JSON.stringify(g.overflow)}`);
  if(test.width>=1024)assert(g.scroll<=g.client+2,`${c.id}: outer overflow ${g.scroll}/${g.client}`);
  for(const value of g.passwords)assert.equal(value,'','No saved secret underlying a mask');
  if(c.group==='settings'&&test.width>900)assert.equal(g.serviceLast,'externalExecution');
  if(c.group==='settings'&&!['S31','S32','S36'].includes(c.id))assert.equal(g.policyTargets,2,'Policies must name their agent and connection');
  if(c.group==='settings'&&!['S31','S32','S36'].includes(c.id))assert.equal(g.initiativeTargets,1,'Initiative is granted to one agent binding');
  if(c.id==='S21')assert.equal(g.emptyCatalog,1,'Empty catalogue differs from no granted templates');
  if(c.id==='S72'){assert.equal(g.feature,'off-retained');assert.equal(g.enableError,1);}
  if(c.id==='S73'){assert.equal(g.feature,'on');assert.equal(g.connectionActive,'false');}
  if(c.modal)assert(g.modal,`${c.id}: confirmation must be visible`);
  if(g.modal){assert(g.modal.left>=-1);assert(g.modal.right<=test.width+1);}
  if(c.group==='tests'){
    assert(g.panel);assert.equal(g.panel.width,420);assert.equal(g.panel.height,980);
    assert.equal(g.panel.reply,c.id==='S07'?1:0);assert.equal(g.panel.error,c.id==='S09'?1:0);
    if(['S08','S10'].includes(c.id))assert(g.panel.inputs.every(n=>n.disabled));
    if(c.id==='S08')assert.equal(g.waiting,1);
    if(c.id==='S11')assert.equal(g.panel.inputs.length,3);
  }
  if(['S14','S15','S16','S17','S18','S71'].includes(c.id)){assert(g.testDisabled);assert(g.startDisabled);}
  if(c.id==='S19'){assert.equal(g.testDisabled,false);assert.equal(g.startDisabled,false);}
  if(c.id==='S12')assert.equal(g.execution,undefined);
  if(c.id==='S13')assert.equal(g.execution,'builtin');
  if(c.id==='S70')assert.equal(g.blocker,0);
  if(['S49','S50'].includes(c.id)){assert.equal(g.unknown,1);assert(!g.buttonText.some(text=>/повторить отправ|force.*retry|resend/i.test(text)));}
  if(c.group==='client'){assert(g.clientShadow);assert.equal(g.clientShadow.overflow,false);assert.equal(g.clientShadow.consent,['S60','S61'].includes(c.id)?'required':'current-illustration');}
}
