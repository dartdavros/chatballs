import type { ProductId, Size } from "../model";

export type City = "kazan" | "innopolis" | "chelny";
export type MailState = "queued" | "sent" | "failed" | "unknown";

export type ProposalDraft = {
  productId: ProductId | "";
  quantities: Record<Size, number>;
  budget: number;
  city: City;
  address: string;
  company: string;
  contact: string;
  email: string;
  confirmed: boolean;
};

export const initialDraft: ProposalDraft = {
  productId: "", quantities: {M: 6, L: 10, XL: 4}, budget: 35000, city: "kazan",
  address: "", company: "", contact: "", email: "", confirmed: false,
};

export type Destination = {id: City; price: number; days: number};
export type PartyOption = {
  id: ProductId;
  name: string;
  basePrice: number;
  photo: string;
  stock: Record<Size, number>;
  available: boolean;
  withinBudget: boolean;
};

export type PartyQuote = {
  productId: ProductId;
  productName: string;
  quantities: Partial<Record<Size, number>>;
  quantity: number;
  city: City;
  unitPrice: number;
  discountedUnit: number;
  discountPercent: number;
  subtotal: number;
  delivery: number;
  days: number;
  total: number;
};

export type LiveQuote = PartyQuote & {id: string; validUntil: string};

export type ProposalResult = {
  proposal: {
    number: string;
    crmReference: string;
    quoteId: string;
    quote: PartyQuote;
    company: string;
    contact: string;
    address: string;
    validUntil: string;
    documentPath: string;
    downloadPath: string;
  };
  mail: {status: MailState; recipient: string};
  lead: {proposal: string; assignee: string};
};

export type PartyResponse = {
  quantity: number; options: PartyOption[]; destinations: Destination[]; emailRecipients: string[];
};
