export type SalesPeriod = "today" | "d7" | "d30";

export type KpiItem = {
  label: string;
  value: string;
  sub: string;
  dot?: string;
  valueColor?: string;
  subColor?: string;
  deltaText?: string;
  deltaColor?: string;
  down?: boolean;
};

export type SalesListItem = {
  dot: string;
  title: string;
  meta: string;
  time: string;
  conversationId?: number;
};
