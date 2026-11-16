// No application, auth, realtime, API or service data loader is mounted.
import React from 'react';
import * as ReactDOM from 'react-dom/client';
import { ExternalUnconfiguredCanvas } from './canvas';
import '../../../../apps/internal-ui/src/styles';
import '../../../../apps/internal-ui/src/features/integrations/services/services.css';
import '../settings-off/baseline.css';
Object.assign(window, { React, ReactDOM, ExternalUnconfiguredCanvas });
