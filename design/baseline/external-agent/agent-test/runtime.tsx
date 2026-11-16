// Static design only. No app loader, test hook, API call or external service.
import React from 'react';
import * as ReactDOM from 'react-dom/client';
import { ExternalAgentTestCanvas } from './canvas';
import '../../../../apps/internal-ui/src/styles';
import '../settings-off/baseline.css';
Object.assign(window, { React, ReactDOM, ExternalAgentTestCanvas });
