import { useEffect, useRef, useState } from "react";
import type { ConnectionDraft, ExternalConnection } from "./model";

function freshDraft(connection: ExternalConnection): ConnectionDraft {
  return { ...structuredClone(connection), bindings: connection.bindings.map(binding => ({ ...structuredClone(binding),
    customFields: binding.customFields.filter(ref => !binding.staleGrants?.customFields.some(stale =>
      stale.sourceConnectionId === ref.sourceConnectionId && stale.fieldId === ref.fieldId)),
    templateIds: binding.templateIds.filter(id => !binding.staleGrants?.templateIds.includes(id)),
  })) };
}

export function useConnectionDraft(connection: ExternalConnection) {
  const [previous, setPrevious] = useState(connection);
  const [draft, setDraft] = useState<ConnectionDraft>(() => freshDraft(connection));
  const adoptNext = useRef(false);
  const edited = JSON.stringify(draft) !== JSON.stringify(previous);
  const editedRef = useRef(edited);
  editedRef.current = edited;
  const snapshot = JSON.stringify(connection);
  useEffect(() => {
    if (adoptNext.current || !editedRef.current) {
      setPrevious(connection); setDraft(freshDraft(connection)); adoptNext.current = false;
    }
  }, [snapshot]);
  function acceptCheck(checked: ExternalConnection) {
    const metadata = { revision: checked.revision, compatible: checked.compatible, checkedAt: checked.checkedAt,
      contentTypes: checked.contentTypes, checkFailure: checked.checkFailure };
    setPrevious(current => ({ ...current, ...metadata }));
    setDraft(current => ({ ...current, ...metadata }));
  }
  return { previous, draft, edited, setDraft, adoptNext, acceptCheck };
}
