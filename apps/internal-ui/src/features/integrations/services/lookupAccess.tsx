import { createContext, useContext } from "react";
import { api } from "../../../api/client";

export type LookupItem = { value: string | number; label: string };
export type LookupLoader = (connection: string, key: string) => Promise<LookupItem[]>;
const defaultLoader: LookupLoader = (connection, key) => api<{ items: LookupItem[] }>(
  `/api/v1/integrations/services/${connection}/lookups/${key}/`).then(result => result.items);
export const LookupAccessContext = createContext<LookupLoader>(defaultLoader);
export const useLookupAccess = () => useContext(LookupAccessContext);
