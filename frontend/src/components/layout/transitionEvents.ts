export const MARKET_TICKER_READY_EVENT = "polifin:market-ticker-ready";
export const DASHBOARD_READY_EVENT = "polifin:dashboard-ready";
export const MARKET_PAGE_READY_EVENT = "polifin:market-page-ready";
export const BULLETIN_PAGE_READY_EVENT = "polifin:bulletin-page-ready";
export const AUTONOMOUS_ACTIONS_READY_EVENT = "polifin:autonomous-actions-ready";
export const PAGE_TRANSITION_REQUEST_EVENT = "polifin:page-transition-request";

export type PageTransitionNavigation = {
  href: string;
  replace?: boolean;
};

export function requestPageTransition(href: string, replace = false) {
  window.dispatchEvent(
    new CustomEvent<PageTransitionNavigation>(PAGE_TRANSITION_REQUEST_EVENT, {
      detail: { href, replace },
    }),
  );
}
