export type TaGlossaryEntry = {
  id: string;
  title: string;
  short: string;
  long: string;
  formula: string;
  category?: string;
  related?: string[];
};
