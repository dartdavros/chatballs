// Only presentation is mounted: no App, authorization, data loaders or service runtime.
import React from 'react';
import * as ReactDOM from 'react-dom/client';
import { ExternalAgentCanvas } from './canvas';
import '../../../apps/internal-ui/src/styles';
import '../../../apps/internal-ui/src/features/agents/test-chat/styles.css';

Object.assign(window, { React, ReactDOM, ExternalAgentCanvas });
