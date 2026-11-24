export type ProductId = "alpine" | "summit" | "ridge" | "glacier" | "freeride" | "peak";
export type Size = "M" | "L" | "XL";
export type StoreId = "center" | "gorki";
export type Customer = "andrey" | "andrey-after-purchase" | "maria" | "olga" | "school";

type Stock = { store: StoreId; available: number; address: string; closesAt: number };

export type ShopProduct = {
  id: ProductId;
  name: string;
  basePrice: number;
  personalPrice: number;
  insulation: number;
  membrane: number;
  breathability: number;
  stock: Record<Size, Stock[]>;
};

export type ShopCart = { productId: ProductId; size: Size; personalPrice: number };
export type ShopQuote = ShopCart & {
  name: string;
  bonusBalance: number;
  maxBonus: number;
  bonusSpent: number;
  total: number;
  revision: string;
};
export type ShopOrder = ShopQuote & {
  number: number;
  store: StoreId;
  address: string;
  balanceAfter: number;
  stockAfter: number;
};

export type StoreData = {
  widgetKey: string;
  pickupEvent?: string | null;
  loyaltyEvent?: string | null;
  preparedChat?: { route: string; ticket: string };
  language: string;
  customer: Customer;
  balance: number;
  cart: ShopCart | null;
  order: ShopOrder | null;
  products: ShopProduct[];
};
export type ShopOptions = { productId: ProductId; size: Size; store: StoreId };

export type Product = {
  id: ProductId;
  name: string;
  article: string;
  price: number;
  basePrice: number;
  description: string;
  material: string;
  lining: string;
  membrane: string;
  breathability: string;
  color: string;
  colorName: string;
  photo: string;
  sizes: Size[];
  stockBySize: Record<Size, Record<StoreId, number>>;
};

export type ShopDisplay = {
  products: Product[];
  product: Product;
  customer: {name: string; phone: string; balance: number};
  cart: (ShopCart & { productName: string }) | null;
  quote: ShopQuote | null;
  order: ShopOrder | null;
  inventory: {store: StoreId; address: string; hours: string; available: number}[];
};
