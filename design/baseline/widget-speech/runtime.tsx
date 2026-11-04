// Presentation components only: no App, session hooks or service requests.
import '../service-integrations/runtime';
import { SpeechIcon } from './lucide-icons';
import { Bubble } from '../../../apps/web-chat/src/ChatMessages';
import { VoiceMessage as WidgetVoiceMessage } from '../../../apps/web-chat/src/VoiceMessage';
import { ChatComposer } from '../../../apps/web-chat/src/ChatComposer';
import { BotAvatar } from '../../../apps/web-chat/src/BotIcon';
import { PreChatForm } from '../../../apps/web-chat/src/PreChatForm';
import { LogoSpinner } from '../../../apps/internal-ui/src/shared/icons';
import { IntegrationPageLayout } from '../../../apps/internal-ui/src/features/integrations/IntegrationPageLayout';
import { WebIntegrationHeader } from '../../../apps/internal-ui/src/features/integrations/WebIntegrationHeader';
import { CopyButton } from '../../../apps/internal-ui/src/shared/ui-controls';
import { setCurrentLanguage } from '../../../packages/shared/src/i18n';
import { ru } from '../../../apps/internal-ui/src/i18n/ru';
import { en } from '../../../apps/internal-ui/src/i18n/en';
import { voiceWaveHeights, PreparedMessage } from '../../../packages/ui/src';
import '../../../apps/web-chat/src/widget.css';
import '../../../apps/web-chat/src/preChat.css';
import '../../../apps/web-chat/src/consent.css';
import '../../../apps/internal-ui/src/features/agents/styles.css';
import '../../../apps/internal-ui/src/shared/section-menu.css';
import '../../../apps/internal-ui/src/features/sales/dialogs/composer.css';
const translateExisting = (value: string, lang: string) => {
  const key = Object.keys(ru).find(key => ru[key as keyof typeof ru] === value) as keyof typeof ru | undefined;
  return lang === 'en' && key ? en[key] : value;
};
Object.assign(window, { SpeechProduct: { SpeechIcon, Bubble, WidgetVoiceMessage, ChatComposer, PreparedMessage, BotAvatar, PreChatForm, LogoSpinner, IntegrationPageLayout,
  WebIntegrationHeader, CopyButton, setCurrentLanguage, translateExisting, voiceWaveHeights } });
