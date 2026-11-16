import { describe, expect, it } from "vitest";
import { configurationChanges, emptyBinding } from "./bindings";
import type { ExternalConnection } from "./model";

describe("external settings commands", () => {
  const binding = emptyBinding({ id: 1, channelId: 9, name: "Agent" }, "external-agent");
  const connection: ExternalConnection = { id: 2, name: "Service", baseUrl: "https://executor.example.invalid", enabled: true,
    revision: 8, keyConfigured: true, compatible: true, checkedAt: null, contentTypes: [], bindings: [binding] };
  it("starts each new assignment with independent empty grants and no initiative", () => {
    expect(binding.processingMode).toBe("ordinary");
    expect(binding.standardFields).toEqual([]);
    expect(binding.customFields).toEqual([]);
    expect(binding.templateIds).toEqual([]);
    expect(binding.policyAccepted).toBe(false);
    expect(binding.proactiveEnabled).toBe(false);
  });
  it("saves the selected processing mode and durations through the form command", () => {
    const changed = { ...connection, bindings: [{ ...binding, processingMode: "long" as const, longTimeout: 7200 }] };
    expect(configurationChanges(connection, changed).bindings[0]).toMatchObject({
      processingMode: "long", ordinaryTimeout: 120, longTimeout: 7200, maximumTimeout: 86400,
    });
    expect(configurationChanges(changed, { ...changed, bindings: [binding] }).bindings[0].processingMode).toBe("ordinary");
  });
  it("sends a revision-checked atomic command without credentials or display metadata", () => {
    const changed = { ...connection, bindings: [{ ...binding, policyAccepted: true, standardFields: ["name"] }] };
    const command = configurationChanges(connection, changed);
    expect(command.revision).toBe(8);
    expect(command.bindingRevisions).toEqual({ "1": [0, 0] });
    expect(command.connection).toEqual({});
    expect(command.bindings[0]).not.toHaveProperty("agentName");
    expect(command.bindings[0]).not.toHaveProperty("staleGrants");
    expect(command.bindings[0].standardFields).toEqual(["name"]);
    expect(configurationChanges(connection, { ...connection, bindings: [] }).removeAgentIds).toEqual([1]);
  });
});
