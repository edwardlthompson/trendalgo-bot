export type SettlementAssetOption = {
  asset: string;
  label: string;
  chain: string;
};

export type SettlementData = {
  period: string;
  amount_usd: number;
  address: string;
  asset: string;
  chain?: string;
  amount_btc?: number;
  amount_sats?: number;
  amount_to_send?: number;
  payment_id?: string;
  payment_reference?: string;
  status?: string;
  licensed_until?: string;
  qr_payload: string;
  disclaimer: string;
  user_initiated_only: boolean;
  auto_verify?: boolean;
  payment_instructions?: string;
  min_confirmations?: number;
  grace_period_days?: number;
  watching?: boolean;
};

export type SettlementCallbacks = {
  onCopy: (text: string) => void;
  onPoll?: (paymentId: string) => Promise<SettlementData | null>;
  onConfirmed?: (data: SettlementData) => void;
  assets?: SettlementAssetOption[];
  selectedAsset?: string;
  onAssetChange?: (asset: string) => void;
};
