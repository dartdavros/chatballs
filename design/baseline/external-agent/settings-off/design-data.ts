// Illustrative document content only; no API data source, credentials or fixtures.
import type { SessionUser } from '../../../../apps/internal-ui/src/types';
import type { OwnWorkStatus } from '../../../../apps/internal-ui/src/features/work-status/useOwnWorkStatus';
import { tx } from './copy';

const membership = {
  id: 1, organizationPublicId: 'design', role: 'OWNER' as const, positionTitle: '', organization: 'design',
  organizationName: tx('organizationName'), organizationLogoUrl: null, totpRequired: false, capabilities: [],
  groups: [], joinedAt: '2026-11-15T09:00:00Z',
};
export const user: SessionUser = {
  ...membership, id: 1, email: '', fullName: tx('ownerName'), avatarUrl: null, mustChangePassword: false,
  totpEnabled: false, totpLastUsedAt: null, deliveryMode: 'SELF_HOSTED', isInstanceAdmin: false,
  memberships: [membership], uiTheme: 'LIGHT', uiAccent: '#0f9b8e', uiLanguage: '', language: 'ru',
};
export const workStatus: OwnWorkStatus = {
  saved: { status: 'READY', version: 1, changedAt: null }, pending: null, failed: null,
  choose: () => {}, retry: () => {}, online: true, connectionLost: false,
};
