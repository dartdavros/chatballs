// Presentation imports only. No application, services or API clients are mounted.
import '../widget-speech/runtime';
import { ChatBody } from '../../../apps/web-chat/src/ChatBody';
import { StartChatFooter } from '../../../apps/web-chat/src/StartChatFooter';
import { ChatHeader } from '../../../apps/web-chat/src/ChatHeader';
import { ServerErrors } from '../../../apps/internal-ui/src/features/integrations/external/ServerFormParts';
import { ServiceAlert } from '../../../apps/internal-ui/src/features/integrations/services/connect/ServiceAlert';
import '../../../apps/internal-ui/src/features/integrations/services/services.css';
Object.assign(window, { EventProduct: { ChatBody, StartChatFooter, ChatHeader, ServerErrors, ServiceAlert } });
