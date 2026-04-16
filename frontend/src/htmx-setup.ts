import "htmx.org";

/**
 * Configure HTMX defaults after it loads.
 * htmx.org auto-initializes on import, we just need to set config.
 */
export function configureHtmx(): void {
  const htmx = (window as Window & { htmx?: HtmxApi }).htmx;
  if (!htmx) return;

  htmx.config.defaultSwapStyle = "outerHTML";
  htmx.config.historyCacheSize = 0;
  htmx.config.includeIndicatorStyles = false;
}

/** Minimal typing for the htmx global we care about. */
interface HtmxApi {
  config: {
    defaultSwapStyle: string;
    historyCacheSize: number;
    includeIndicatorStyles: boolean;
  };
  on(event: string, callback: (evt: Event) => void): void;
}
