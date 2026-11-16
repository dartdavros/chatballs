import { SpeechSettings } from "../SpeechSettings";
import { et } from "../../settings/external-agent/copy";

export function SpeechCard(props: Parameters<typeof SpeechSettings>[0]) {
  return <section className="agent-card agent-speech-settings" data-independent-stt>
    <div className="agent-card-head"><h3>{et("agentBase.speechTitle")}</h3></div>
    <p className="settings-section-note">{et("agentBase.speechHelp")}</p>
    <div className="agent-side-fields"><SpeechSettings {...props} /></div>
  </section>;
}
