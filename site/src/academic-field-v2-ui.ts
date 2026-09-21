import type { AcademicFieldV2SubcategoryOption } from "./types";

export function visibleSubcategories(
  options: AcademicFieldV2SubcategoryOption[],
  parentGroupCode: string,
): AcademicFieldV2SubcategoryOption[] {
  return options
    .filter((item) =>
      item.parent_group_code === parentGroupCode
      && item.unfiltered_count > 0
      && item.ui_status !== "hidden")
    .sort((left, right) => left.display_order - right.display_order);
}

export function syncBroadSubcategoryVisibility(
  form: HTMLFormElement,
  broadInput: HTMLInputElement,
): void {
  const nested = [...form.querySelectorAll<HTMLElement>("[data-subcategories-for]")]
    .find((item) => item.dataset.subcategoriesFor === broadInput.value);
  if (!nested) return;
  nested.hidden = !broadInput.checked;
  if (!broadInput.checked) {
    nested.querySelectorAll<HTMLInputElement>('input[type="checkbox"]')
      .forEach((subcategory) => { subcategory.checked = false; });
  }
}
