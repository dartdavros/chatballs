import { useCallback, useState } from "react";

import { pathFromRoute, type RouteState } from "./router";
import type { RouteKey } from "./types";

export function useRouteNavigation(
  initialRoute: RouteState,
  organizationPublicId: string | null,
) {
  const [route, setRoute] = useState<RouteKey>(initialRoute.route);
  const [selectedEmployeeId, setSelectedEmployeeId] = useState(initialRoute.employeeId);
  const [selectedProductId, setSelectedProductId] = useState(initialRoute.productId);
  const [selectedProductCode, setSelectedProductCode] = useState(initialRoute.productCode);
  const [selectedAgentId, setSelectedAgentId] = useState(initialRoute.agentId);
  const [selectedKnowledgeId, setSelectedKnowledgeId] = useState(initialRoute.knowledgeId);
  const [selectedConversationId, setSelectedConversationId] = useState<number | null>(null);
  const [selectedClientId, setSelectedClientId] = useState(initialRoute.clientId);
  const [selectedOrderId, setSelectedOrderId] = useState(initialRoute.orderId);

  const applyRouteState = useCallback((next: RouteState) => {
    setRoute(next.route);
    setSelectedEmployeeId(next.employeeId);
    setSelectedProductId(next.productId);
    setSelectedProductCode(next.productCode);
    setSelectedAgentId(next.agentId);
    setSelectedKnowledgeId(next.knowledgeId);
    setSelectedConversationId(null);
    setSelectedClientId(next.clientId);
    setSelectedOrderId(next.orderId);
  }, []);

  const navigate = useCallback((
    nextRoute: RouteKey,
    entityId: number | null = null,
    replace = false,
    productCode: string | null = null,
    organizationId: string | null = organizationPublicId,
  ) => {
    const nextState: RouteState = {
      organizationPublicId: organizationId,
      route: nextRoute,
      employeeId: nextRoute === "employeeDetail" ? entityId : null,
      productId: nextRoute === "productDetail" ? entityId : null,
      productCode: nextRoute === "aiAgentCreate" ? productCode : null,
      agentId: nextRoute === "aiAgentDetail" ? entityId : null,
      knowledgeId: nextRoute === "aiKnowledgeDetail" ? entityId : null,
      clientId: nextRoute === "salesClientDetail" ? entityId : null,
      orderId: nextRoute === "salesOrderDetail" ? entityId : null,
    };
    applyRouteState(nextState);
    setSelectedConversationId(
      nextRoute === "salesDialogs" || nextRoute === "supportDialogs" ? entityId : null,
    );
    const nextPath = pathFromRoute(
      nextRoute,
      entityId,
      nextState.productCode,
      organizationId,
    );
    if (`${window.location.pathname}${window.location.search}` === nextPath) return;
    const method = replace ? "replaceState" : "pushState";
    window.history[method](nextState, "", nextPath);
  }, [applyRouteState, organizationPublicId]);

  return {
    route,
    selectedEmployeeId,
    selectedProductId,
    selectedProductCode,
    selectedAgentId,
    selectedKnowledgeId,
    selectedConversationId,
    selectedClientId,
    selectedOrderId,
    applyRouteState,
    navigate,
  };
}
