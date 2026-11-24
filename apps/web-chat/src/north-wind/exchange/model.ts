import type { ProductId, Size, StoreId } from "../model";

export type Pickup = {store: StoreId; name: string; address: string; closesAt: number};
export type OrderStatus = "reserved" | "ready" | "collected" | "delayed";
export type Order = {number: number; productId: ProductId; name: string; size: Size; status: OrderStatus};
export type Request = {number: number; orderNumber: number; targetSize: Size; store: StoreId; status: "requested"; address: string};
export type VerifiedOrder = {order: Order; shipment: {status: OrderStatus; pickup?: Pickup; eta?: string}; exchange: Request | null};
export type ExchangeOptions = {
  exchangeDays: number;
  outcome: "available" | "out_of_stock" | "not_eligible" | "staff_review";
  reason?: "expired";
  pickupPoints: (Pickup & {available: number})[];
};
