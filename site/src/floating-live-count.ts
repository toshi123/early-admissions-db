export interface FloatingLiveCountController {
  update(text: string, invalid: boolean): void;
  disconnect(): void;
}

interface VisibilityObserver {
  observe(target: Element): void;
  disconnect(): void;
}

export type VisibilityObserverFactory = (
  callback: (isVisible: boolean) => void,
) => VisibilityObserver;

function defaultObserverFactory(callback: (isVisible: boolean) => void): VisibilityObserver {
  if (typeof IntersectionObserver !== "undefined") {
    const observer = new IntersectionObserver(([entry]) => callback(entry?.isIntersecting ?? false), {
      threshold: 0,
    });
    return observer;
  }

  let target: Element | null = null;
  const update = () => {
    if (!target) return;
    const rect = target.getBoundingClientRect();
    callback(rect.bottom > 0 && rect.top < window.innerHeight);
  };
  window.addEventListener("scroll", update, { passive: true });
  window.addEventListener("resize", update);
  return {
    observe(element) {
      target = element;
      update();
    },
    disconnect() {
      window.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
      target = null;
    },
  };
}

export function bindFloatingLiveCount(
  source: HTMLElement,
  floating: HTMLElement,
  floatingText: HTMLElement,
  observerFactory: VisibilityObserverFactory = defaultObserverFactory,
): FloatingLiveCountController {
  let sourceVisible = true;

  const renderVisibility = () => {
    floating.classList.toggle("is-visible", !sourceVisible);
  };

  const observer = observerFactory((isVisible) => {
    sourceVisible = isVisible;
    renderVisibility();
  });
  observer.observe(source);

  return {
    update(text, invalid) {
      floatingText.textContent = invalid ? "条件を確認してください" : text;
      floating.classList.toggle("is-invalid", invalid);
    },
    disconnect() {
      observer.disconnect();
      floating.classList.remove("is-visible");
    },
  };
}
