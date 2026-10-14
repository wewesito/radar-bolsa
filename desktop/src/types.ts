// Tipos de las respuestas del motor (src/radar/api/app.py). Fechas en ISO UTC.

export type Label = "buy" | "watch" | "avoid";

export type Reason = { text: string; data: string; metric: string | null };
export type RuleCheck = { rule: string; passed: boolean; detail: string };

export type Market = {
  exchange: string | null;
  country: string | null;
  tz: string | null;
  opens?: string;
  closes?: string;
  delay_minutes: number | null;
};

export type AsOf = {
  fundamentals_as_of: string | null;
  history_as_of: string | null;
  last_report: string | null;
};

export type RecSummary = {
  ticker: string;
  name: string;
  kind: "stock" | "etf";
  label: Label;
  label_es: string;
  score: number | null;
  risk_level: number | null;
  risk_label: string;
  price: number | null;
  currency: string | null;
  summary: string;
  fit: string;
  pros: Reason[];
  cons: Reason[];
  entry: { low: number; high: number; position: "below" | "inside" | "above" } | null;
  entry_note: string;
  risk_detail: string;
  sector: string | null;
  sector_es: string | null;
  country: string | null;
  spain_index: string | null;
  etf_role: string | null;
  etf_role_es: string | null;
  etf_index: string | null;
  as_of: AsOf;
  market: Market;
};

export type InputScore = {
  key: string;
  label: string;
  value: number | null;
  peer_median: number | null;
  n_peers: number;
  percentile: number | null;
};

export type ComponentScore = {
  key: string;
  label: string;
  description: string;
  basis_label: string;
  weight: number;
  inputs: InputScore[];
  score: number | null;
  effective_weight: number;
};

export type FairValueEstimate = {
  method: string;
  metric: string;
  value: number;
  peer_median: number;
  estimate: number;
};

export type Profile = {
  level: "conservador" | "moderado" | "dinamico";
  label: string;
  points: number;
  max_risk: number;
  max_risk_label: string;
  objective_label: string;
  allocation: { etf: number; stocks: number; safe: number };
  weights: Record<string, number>;
  amount_eur: number;
  positions: number;
  notes: string[];
  answers: Answers;
  description?: string;
};

export type Answers = {
  horizon: number;
  reaction: number;
  amount: number;
  objective: "growth" | "dividends" | "preserve";
  experience: number;
};

export type RecDetail = Omit<RecSummary, "entry"> & {
  components: ComponentScore[];
  checks: RuleCheck[];
  notes: string[];
  entry: {
    low: number | null;
    high: number | null;
    position: "below" | "inside" | "above" | null;
    estimates: FairValueEstimate[];
    peer_group: string;
    note: string;
  } | null;
  profile: Profile;
  profile_is_default: boolean;
  source: string;
  row: Record<string, number | string | null> | null;
  etf: { role: string; zone: string; index: string; accumulating: boolean } | null;
};

export type RecList = {
  built_at: string;
  source: string;
  profile: Profile;
  counts: Record<Label, number>;
  items: RecSummary[];
};

export type UniverseStatus = {
  built_at: string | null;
  age_days: number | null;
  stale: boolean;
  rows: number;
  failed: string[];
  source: string;
  build: {
    running: boolean;
    done: number;
    total: number;
    started_at: string | null;
    finished_at: string | null;
    error: string | null;
  };
};

export type SpainRow = {
  ticker: string;
  name: string;
  spain_index: "IBEX 35" | "Mercado Continuo";
  sector: string | null;
  sector_es: string;
  currency: string | null;
  peer_group: string;
  pe_sector: number | null;
  pb_sector: number | null;
  valuation_reading: string | null;
  div_sustainability: string | null;
  score: number | null;
  label: Label | null;
  label_es: string | null;
  risk_level: number | null;
  top_eligible: boolean;
  fundamentals_as_of: string | null;
  history_as_of: string | null;
  [metric: string]: number | string | boolean | null;
};

export type SpainData = {
  built_at: string;
  source: string;
  profile_label: string;
  profile_is_default: boolean;
  items: SpainRow[];
};

export type Quote = {
  ticker: string;
  name: string;
  price: number;
  change_pct: number | null;
  currency: string | null;
  exchange: string | null;
  market_state: string | null;
  delay_minutes: number | null;
  as_of: string;
  source: string;
  stale: boolean;
};

export type MarketTile = Partial<Quote> & {
  ticker: string;
  label: string;
  spark?: number[];
  error?: string;
};

export type History = {
  ticker: string;
  range: string;
  interval: string;
  points: [string, number][];
  as_of: string;
  source: string;
  stale: boolean;
};

export type SearchResult = {
  ticker: string;
  name: string;
  quote_type: string | null;
  exchange: string | null;
  in_universe: boolean;
};

export type GlossaryEntry = {
  key: string;
  term: string;
  category: string;
  what: string;
  formula: string;
  reading: string;
  limits: string;
};

export type Question = {
  key: keyof Answers;
  topic: string;
  question: string;
  hint: string;
  options: [string, string][];
  values?: string[];
};

export type BacktestMetrics = {
  total_return: number;
  cagr: number;
  volatility: number;
  max_drawdown: number;
  return_per_risk: number | null;
};

export type BacktestResult = {
  built_at: string;
  source: string;
  dates: string[];
  series: Record<string, (number | null)[]>;
  metrics: Record<string, BacktestMetrics>;
  yearly: Record<string, Record<string, number>>;
  last_selection: { date: string; picks: { ticker: string; score: number }[] } | null;
  rebalances: number;
  config: { top_n: number; rebalance_weeks: number; cost: number };
  universe_size: number;
  failed: string[];
};

export type BacktestState = { result: BacktestResult | null; running: boolean; error: string | null };
