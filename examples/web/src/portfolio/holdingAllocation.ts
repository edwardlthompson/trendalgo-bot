/** Portfolio weight: holding USD value ÷ total portfolio net worth. */
export function holdingAllocationPct(valueUsd: number, portfolioTotalUsd: number): number {
  if (portfolioTotalUsd <= 0 || valueUsd <= 0) return 0;
  return valueUsd / portfolioTotalUsd;
}
