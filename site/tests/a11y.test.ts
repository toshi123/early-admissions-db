import { describe, expect, it } from "vitest";
import { trapDialogTab } from "../src/a11y";

describe("mobile filter keyboard focus", () => {
  it("wraps Tab and Shift+Tab inside the open filter dialog", () => {
    const panel = document.createElement("aside");
    panel.innerHTML = '<button id="first">first</button><input id="middle"><button id="last">last</button>';
    document.body.append(panel);
    const first = panel.querySelector<HTMLButtonElement>("#first")!;
    const last = panel.querySelector<HTMLButtonElement>("#last")!;
    last.focus();
    const forward = new KeyboardEvent("keydown", { key: "Tab", cancelable: true });
    expect(trapDialogTab(panel, forward)).toBe(true);
    expect(document.activeElement).toBe(first);
    first.focus();
    const backward = new KeyboardEvent("keydown", { key: "Tab", shiftKey: true, cancelable: true });
    expect(trapDialogTab(panel, backward)).toBe(true);
    expect(document.activeElement).toBe(last);
  });
});
