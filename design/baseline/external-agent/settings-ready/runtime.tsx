// Presentation only. No app, session, settings/service data loader or key operation is mounted.
import React from 'react';
import * as ReactDOM from 'react-dom/client';
import { ExternalReadyCanvas } from './canvas';
import '../../../../apps/internal-ui/src/styles';
import '../../../../apps/internal-ui/src/features/integrations/services/services.css';
import '../../../../apps/internal-ui/src/features/integrations/speech/speech-settings.css';
import '../settings-off/baseline.css';
Object.assign(window, { React, ReactDOM, ExternalReadyCanvas });
