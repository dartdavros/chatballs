import { setCurrentLanguage } from "@chatballs/shared";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it } from "vitest";

import type { Employee } from "../../types";
import { EmployeeSecuritySections } from "./EmployeeSecuritySections";
import { employeeForm } from "./model";

const employee: Employee = {
  id: 1, fullName: "Сотрудник", email: "employee@example.test", phone: "",
  role: "EMPLOYEE", positionTitle: "", groups: [], isActive: true,
  isBlocked: false, mustChangePassword: false, totpRequired: false, totpEnabled: false,
  permissions: {
    canView: true, canUpdateProfile: true, canChangeRole: true, canChangeGroups: true,
    canBlock: true, canUnblock: true, canResetPassword: true, canTerminateSessions: true,
    canTransferOwnership: false, canDismiss: true,
  },
};
const noop = () => {};

function render(target = employee) {
  return renderToStaticMarkup(<EmployeeSecuritySections employee={target}
    form={employeeForm(target)} blocked={target.isBlocked} busy={false} updateForm={noop}
    onResetPassword={noop} onTerminateSessions={noop} onToggleBlock={noop}
    onTransferOwnership={noop} onDismiss={noop} />);
}

beforeEach(() => setCurrentLanguage("ru"));

describe("employee dismissal access", () => {
  it("places dismissal in the existing danger zone for active and blocked employees", () => {
    for (const isBlocked of [false, true]) {
      const html = render({ ...employee, isBlocked });
      const dangerZone = html.slice(html.indexOf('class="employee-danger"'));
      expect(dangerZone).toContain("Уволить сотрудника</button>");
    }
  });

  it("never offers dismissal for the owner", () => {
    expect(render({ ...employee, role: "OWNER" })).not.toContain("Уволить сотрудника");
  });

  it("hides dismissal when the server denies it", () => {
    expect(render({ ...employee, permissions: { ...employee.permissions!, canDismiss: false } }))
      .not.toContain("Уволить сотрудника");
  });
});
