// Static presentation only. No app loader, API hooks, agent execution or test panel.
import React from 'react';
import * as ReactDOM from 'react-dom/client';
import { ExternalAgentCanvas } from './canvas';
import '../../../../apps/internal-ui/src/styles';
import '../settings-off/baseline.css';
Object.assign(window, { React, ReactDOM, ExternalAgentCanvas });
