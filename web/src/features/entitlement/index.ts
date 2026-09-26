/**
 * The entitlement feature — what web asks before anything that spends.
 *
 * It lived in `features/publish` until a second feature needed it: brand-kit
 * creation is a paid capability too, and reaching into publish for a quota read
 * would have coupled two features through a third's name. The value is the
 * same one publish uses, read from the same route, so the two gates cannot
 * disagree about what plan the account is on.
 */

export interface Entitlement {
  plan: string;
  used: number;
  limit: number;
  exhausted: boolean;
  killSwitch: boolean;
}

export type EntitlementRefusal = {
  /** The HTTP status to answer the browser with. */
  status: number;
  message: string;
};

/** Whether the account is on a plan that unlocks the paid capabilities. */
export function isPaid(entitlement: Entitlement): boolean {
  return entitlement.plan === 'paid';
}
