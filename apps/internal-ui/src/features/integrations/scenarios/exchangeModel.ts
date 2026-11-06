import type { EditorCatalog, Entity, Mapping, SyncPair } from "./types";
import { compatibleField } from "./bindingOptions";
import { id } from "./model";

export type ExchangePair = { key: string; left: Entity; right: Entity };
export function exchangePairs(catalog: EditorCatalog, adapter: string): ExchangePair[] {
  return (catalog.adapters.find(a => a.key === adapter)?.entities ?? []).filter(right => right.synchronization?.directions.length).flatMap(right =>
    catalog.entities.filter(left => right.nativeEntities.includes(left.key)).map(left => ({ key: `${left.key}:${right.key}`, left, right })));
}
export function makePair(pair: ExchangePair, connection: number): SyncPair {
  return { id: id(), enabled: false, left: { connection: "chatballs", entity: pair.left.key },
    right: { connection: String(connection), entity: pair.right.key }, direction: pair.right.synchronization?.directions.includes("both") ? "both" : pair.right.synchronization!.directions[0], fields: [],
    sourceOfTruth: "latest", conflict: "latest", deletion: "unlink", causality: { suppressEcho: true, requireExplicitLink: true } };
}
export function pairKey(pair: SyncPair) { return `${pair.left.entity}:${pair.right.entity}`; }
export function mappingAllowed(pair: ExchangePair, left: string, right: string, direction: Mapping["direction"], catalog: EditorCatalog) {
  const a = pair.left.fields.fields?.find(f => f.name === left);
  const b = pair.right.fields.fields?.find(f => f.name === right);
  if (!a || !b) return false;
  const source = direction === "forward" ? a : b, target = direction === "forward" ? b : a;
  const writable = direction === "forward" ? pair.right : pair.left;
  if (writable.writableFields && !writable.writableFields.includes(target.name)) return false;
  return compatibleField(source, target) || ["enum", "lookup"].includes(source.type) && ["enum", "lookup"].includes(target.type)
    || catalog.transforms.some(t => t.inputTypes.includes(source.type) && (t.outputType === target.type || t.outputType === "any"));
}
