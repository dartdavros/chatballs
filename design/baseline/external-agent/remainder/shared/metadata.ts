import { agentCases, testCases } from '../agent/cases';
import { settingsCases } from '../settings/cases';
import { chatCases } from '../chat/cases';
import { clientCases } from '../client/cases';
import { copy as agentCopy } from '../agent/copy';
import { copy as settingsCopy } from '../settings/copy';
import { copy as chatCopy } from '../chat/copy';
import { copy as sharedCopy } from './copy';
import { clientCopy } from '../client/copy';
import { helpCopy } from './help-copy';
import { bindingCopy } from '../settings/binding-copy';
export const cases=[...testCases.map(c=>({...c,group:'tests'})),...agentCases.map(c=>({...c,group:'agents'})),
  ...settingsCases.map(c=>({...c,group:'settings'})),...chatCases.map(c=>({...c,group:'chat'})),...clientCases.map(c=>({...c,group:'client'}))];
export const dictionaries={agent:agentCopy,settings:settingsCopy,chat:chatCopy,shared:sharedCopy,client:clientCopy,help:helpCopy,bindings:bindingCopy};
