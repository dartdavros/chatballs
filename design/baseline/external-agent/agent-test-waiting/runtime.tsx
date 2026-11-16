// Static waiting-state design. No API, test hook, service response or cancellation.
import React from 'react';
import * as ReactDOM from 'react-dom/client';
import { ExternalAgentWaitingCanvas } from './canvas';
import '../../../../apps/internal-ui/src/styles';
import '../settings-off/baseline.css';
Object.assign(window, { React, ReactDOM, ExternalAgentWaitingCanvas });
