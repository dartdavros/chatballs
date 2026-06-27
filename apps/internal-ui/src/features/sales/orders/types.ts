export type SalesOrdersTab = "orders" | "subs" | "pays" | "refunds" | "exec";

export type StatusTone = "green" | "amber" | "red" | "blue" | "gray" | "purple";

export type StatusBadge = {
  color: string;
  bg: string;
  label: string;
};

export type SalesOrder = {
  id: string;
  date: string;
  client: string;
  offer: string;
  amount: string;
  pay: StatusBadge;
  fulfillment: StatusBadge;
  source: { label: string; color: string };
  seller: string;
  sellerAI?: boolean;
  search: string;
};

export type SalesSubscription = {
  id: string;
  client: string;
  offer: string;
  status: StatusBadge;
  period: string;
  next: string;
  entitlement: string;
  search: string;
};

export type SalesPayment = {
  id: string;
  order: string;
  provider: string;
  amount: string;
  status: StatusBadge;
  method: string;
  date: string;
  reconcile: { color: string; label: string };
  search: string;
};

export type SalesRefund = {
  id: string;
  reference: string;
  amount: string;
  reason: string;
  status: StatusBadge;
  actor: string;
  date: string;
  search: string;
};

export type SalesFulfillment = {
  order: string;
  product: string;
  operation: string;
  status: StatusBadge;
  attempts: string;
  error: string;
  updated: string;
  attention: boolean;
  search: string;
};
