export type FormOption = { value: string | null; display_label: string };

export function inValueOrder(items: FormOption[], order: string[]): FormOption[] {
  const rank = new Map(order.map((value, index) => [value, index]));
  return [...items].sort((left, right) => {
    const leftRank = left.value === null ? order.length : (rank.get(left.value) ?? order.length);
    const rightRank = right.value === null ? order.length : (rank.get(right.value) ?? order.length);
    return leftRank - rightRank;
  });
}
