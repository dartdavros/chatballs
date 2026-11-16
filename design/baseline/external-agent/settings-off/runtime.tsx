// Presentation only: no application, auth, realtime or settings data loaders.
import React from 'react';
import * as ReactDOM from 'react-dom/client';
import { ExternalSettingsCanvas } from './canvas';
import '../../../../apps/internal-ui/src/styles';
Object.assign(window, { React, ReactDOM, ExternalSettingsCanvas });
