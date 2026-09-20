import { describe, expect, it } from "vitest";
import {
  bindFloatingLiveCount,
  type VisibilityObserverFactory,
} from "../src/floating-live-count";

describe("floating live count", () => {
  it("appears only after the canonical live region leaves the viewport", () => {
    document.body.innerHTML = `
      <output id="live" aria-live="polite">該当 5,921件・249大学</output>
      <div id="floating" aria-hidden="true"><span id="floating-text"></span></div>
    `;
    let visibilityChanged: ((isVisible: boolean) => void) | undefined;
    const observerFactory: VisibilityObserverFactory = (callback) => {
      visibilityChanged = callback;
      return { observe: () => undefined, disconnect: () => undefined };
    };
    const source = document.querySelector<HTMLElement>("#live")!;
    const floating = document.querySelector<HTMLElement>("#floating")!;
    const floatingText = document.querySelector<HTMLElement>("#floating-text")!;
    const controller = bindFloatingLiveCount(source, floating, floatingText, observerFactory);

    controller.update("5,921件・249大学", false);
    expect(floating.classList.contains("is-visible")).toBe(false);
    expect(document.querySelectorAll("[aria-live]")).toHaveLength(1);
    expect(floating.getAttribute("aria-hidden")).toBe("true");

    visibilityChanged!(false);
    expect(floating.classList.contains("is-visible")).toBe(true);
    expect(floatingText.textContent).toBe("5,921件・249大学");

    controller.update("73件・12大学", false);
    expect(floatingText.textContent).toBe("73件・12大学");

    visibilityChanged!(true);
    expect(floating.classList.contains("is-visible")).toBe(false);
    controller.disconnect();
  });

  it("replaces stale counts with an invalid-state message", () => {
    document.body.innerHTML = `
      <output id="live" aria-live="polite"></output>
      <div id="floating" aria-hidden="true"><span id="floating-text"></span></div>
    `;
    let visibilityChanged: ((isVisible: boolean) => void) | undefined;
    const controller = bindFloatingLiveCount(
      document.querySelector<HTMLElement>("#live")!,
      document.querySelector<HTMLElement>("#floating")!,
      document.querySelector<HTMLElement>("#floating-text")!,
      (callback) => {
        visibilityChanged = callback;
        return { observe: () => undefined, disconnect: () => undefined };
      },
    );
    visibilityChanged!(false);
    controller.update("5,921件・249大学", true);
    expect(document.querySelector("#floating-text")!.textContent).toBe("条件を確認してください");
    expect(document.querySelector("#floating")!.classList.contains("is-invalid")).toBe(true);
  });
});
