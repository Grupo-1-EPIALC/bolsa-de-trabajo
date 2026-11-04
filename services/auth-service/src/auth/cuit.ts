const CUIT_WEIGHTS = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2];

export function isValidCuit(cuit: string): boolean {
  if (!/^\d{11}$/.test(cuit)) {
    return false;
  }

  const sum = CUIT_WEIGHTS.reduce(
    (total, weight, index) => total + Number(cuit[index]) * weight,
    0,
  );
  const checkDigit = 11 - (sum % 11);
  const expected = checkDigit === 11 ? 0 : checkDigit === 10 ? 9 : checkDigit;
  return Number(cuit[10]) === expected;
}
