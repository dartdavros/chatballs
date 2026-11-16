// Design document only: no app session, backend, mock server or external execution.
import React from 'react';
import * as ReactDOM from 'react-dom/client';
import { RemainderCanvas } from './canvas';
import '../../../../../apps/internal-ui/src/styles';
import '../../settings-off/baseline.css';
import './design-system.css';
Object.assign(window,{React,ReactDOM,RemainderCanvas});
