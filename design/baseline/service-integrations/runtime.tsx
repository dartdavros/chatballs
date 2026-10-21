// Design document entry point. Imports the product's real presentation components.
// It never mounts App, auth providers, data loaders or service editors.
import * as React from 'react';
import { createRoot } from 'react-dom/client';
import { ConfigProvider, Dropdown, theme } from 'antd';
import { FormField, SelectField, TextAreaField, SwitchButton } from '../../../apps/internal-ui/src/shared/form-controls';
import { Button, UnderlineTabs, BackLink, SearchInput, ToneBadge } from '../../../apps/internal-ui/src/shared/ui-controls';
import { StatusPill, ContentState, LoadingState, Avatar } from '../../../apps/internal-ui/src/shared/ui';
import { Icon, LogoIcon } from '../../../apps/internal-ui/src/shared/icons';
import { DecisionDialog } from '../../../apps/internal-ui/src/shared/DecisionDialog';
import { applyAppearance, ACCENT_PRESETS } from '../../../apps/internal-ui/src/shared/appearance';
import { SidebarNavigation } from '../../../apps/internal-ui/src/layout/SidebarNavigation';
import { OrganizationSwitcher } from '../../../apps/internal-ui/src/layout/OrganizationSwitcher';
import { NavigationIcon } from '../../../apps/internal-ui/src/layout/NavigationIcon';
import { SETTINGS_SECTIONS, visibleSettingsSections } from '../../../apps/internal-ui/src/features/settings/sections';
import { ConnectionsTable } from '../../../apps/internal-ui/src/features/integrations/ConnectionsTable';
import { ConnectionIcon, RowActions } from '../../../apps/internal-ui/src/features/integrations/rows';
import './product-styles';

Object.assign(window, {
  React, ReactDOM: { createRoot },
  ServiceUI: { ConfigProvider, Dropdown, theme, FormField, SelectField, TextAreaField, SwitchButton,
    Button, UnderlineTabs, BackLink, SearchInput, StatusPill, ContentState, LoadingState, Avatar,
    Icon, LogoIcon, DecisionDialog, applyAppearance, ACCENT_PRESETS,
    SidebarNavigation, OrganizationSwitcher, NavigationIcon, SETTINGS_SECTIONS, visibleSettingsSections, ConnectionsTable, ConnectionIcon, RowActions, ToneBadge },
});
