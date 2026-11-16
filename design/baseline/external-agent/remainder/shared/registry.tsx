import { AgentSuite } from '../agent/AgentSuite';
import { agentCases, testCases } from '../agent/cases';
import { SettingsSuite, settingsCases } from '../settings/SettingsSuite';
import { ChatSuite, chatCases } from '../chat/ChatSuite';
import { ClientSuite, clientCases } from '../client/ClientSuite';

export type CaseMeta = { id:string; titleRu:string; titleEn:string; descriptionRu?:string; descriptionEn?:string; group:string };
export const cases: CaseMeta[] = [
  ...testCases.map(item=>({...item,group:'tests'})), ...agentCases.map(item=>({...item,group:'agents'})),
  ...settingsCases.map(item=>({...item,group:'settings'})), ...chatCases.map(item=>({...item,group:'chat'})),
  ...clientCases.map(item=>({...item,group:'client'})),
];
export function Screen({meta,width,height}:{meta:CaseMeta;width:number;height:number}) {
  if(meta.group==='settings') return <SettingsSuite variant={meta.id} width={width} height={height}/>;
  if(meta.group==='chat') return <ChatSuite variant={meta.id} width={width} height={height}/>;
  if(meta.group==='client') return <ClientSuite variant={meta.id as typeof clientCases[number]['id']} width={width} height={height}/>;
  return <AgentSuite variant={meta.id} width={width} height={height}/>;
}
