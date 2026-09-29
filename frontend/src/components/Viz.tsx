import { WEEKDAYS, type Driver, type WorkoutDay } from "../api/types";
import { humanizeFeature } from "../lib/format";

/** Ordered classes with the predicted one highlighted and the model's probability bars underneath. */
export function LevelLadder({
  levels,
  active,
  probabilities,
  tone = "brand",
}: {
  levels: readonly string[];
  active: string;
  probabilities: Record<string, number>;
  tone?: "brand" | "risk";
}) {
  return (
    <ul className={`ladder ladder-${tone}`} aria-label="Model probabilities">
      {levels.map((l, i) => {
        const p = (probabilities[l] ?? 0) * 100; // API sends fractions (0-1)
        return (
          <li key={l} className={l === active ? "ladder-active" : ""} data-rank={i}>
            <span className="ladder-name">{l}</span>
            <span className="bar" role="img" aria-label={`${l}: ${p.toFixed(0)} percent`}>
              <span className="bar-fill" style={{ width: `${Math.max(0, Math.min(100, p))}%` }} />
            </span>
            <span className="ladder-pct">{p.toFixed(0)}%</span>
          </li>
        );
      })}
    </ul>
  );
}

export function Drivers({ drivers }: { drivers: Driver[] }) {
  if (!drivers.length) return null;
  const max = Math.max(...drivers.map((d) => Math.abs(d.effect_pct_points)), 1);
  return (
    <div className="drivers">
      <h4>What influenced this</h4>
      <ul>
        {drivers.map((d) => {
          const up = d.effect_pct_points >= 0;
          return (
            <li key={d.feature}>
              <span className="driver-name">
                {humanizeFeature(d.feature)} <span className="muted">({String(d.value)})</span>
              </span>
              <span className="driver-bar" aria-hidden="true">
                <span className={up ? "driver-up" : "driver-down"} style={{ width: `${(Math.abs(d.effect_pct_points) / max) * 100}%` }} />
              </span>
              <span className="driver-val">
                {up ? "+" : "−"}
                {Math.abs(d.effect_pct_points).toFixed(1)} pts
              </span>
            </li>
          );
        })}
      </ul>
      <p className="hint">Estimated by re-running the model with each input replaced by a typical value. It shows influence on this prediction, not medical causation.</p>
    </div>
  );
}

export function WeekGrid({ days }: { days: WorkoutDay[] }) {
  const byDay = new Map(days.map((d) => [d.day, d]));
  return (
    <div className="weekgrid" role="list" aria-label="Weekly schedule">
      {WEEKDAYS.map((w) => {
        const d = byDay.get(w);
        return (
          <div key={w} role="listitem" className={`weekday ${d ? "weekday-on" : "weekday-off"}`}>
            <span className="weekday-name">{w.slice(0, 3)}</span>
            <span className="weekday-focus">{d ? d.focus || "Workout" : "Rest"}</span>
          </div>
        );
      })}
    </div>
  );
}

export function MacroBar({ protein, carbs, fat }: { protein: number; carbs: number; fat: number }) {
  const kcal = { protein: protein * 4, carbs: carbs * 4, fat: fat * 9 };
  const total = kcal.protein + kcal.carbs + kcal.fat || 1;
  const parts = [
    { key: "protein", label: "Protein", g: protein, share: kcal.protein / total },
    { key: "carbs", label: "Carbs", g: carbs, share: kcal.carbs / total },
    { key: "fat", label: "Fat", g: fat, share: kcal.fat / total },
  ];
  return (
    <div>
      <div className="macrobar" role="img" aria-label={parts.map((p) => `${p.label} ${p.g} grams`).join(", ")}>
        {parts.map((p) => (
          <span key={p.key} className={`macro macro-${p.key}`} style={{ width: `${p.share * 100}%` }} />
        ))}
      </div>
      <ul className="legend">
        {parts.map((p) => (
          <li key={p.key}>
            <span className={`dot macro-${p.key}`} aria-hidden="true" /> {p.label}: <strong>{p.g} g</strong> <span className="muted">({Math.round(p.share * 100)}%)</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function BarChart({ data, height = 140, label }: { data: { label: string; value: number; target?: number }[]; height?: number; label: string }) {
  const width = Math.max(data.length * 44, 120);
  const max = Math.max(1, ...data.flatMap((d) => [d.value, d.target ?? 0]));
  const bw = 24;
  return (
    <svg className="chart" viewBox={`0 0 ${width} ${height + 24}`} role="img" aria-label={label} preserveAspectRatio="xMidYMid meet">
      {data.map((d, i) => {
        const x = i * 44 + 10;
        const h = (d.value / max) * height;
        const t = d.target != null ? (d.target / max) * height : null;
        return (
          <g key={d.label}>
            <rect x={x} y={height - h} width={bw} height={h} rx={3} className="chart-bar" />
            {t != null && <line x1={x - 3} x2={x + bw + 3} y1={height - t} y2={height - t} className="chart-target" />}
            <text x={x + bw / 2} y={height - h - 4} textAnchor="middle" className="chart-val">
              {d.value}
            </text>
            <text x={x + bw / 2} y={height + 16} textAnchor="middle" className="chart-label">
              {d.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

export function LineChart({ points, label, unit = "kg" }: { points: [string, number][]; label: string; unit?: string }) {
  if (points.length < 2) return <p className="muted">Log at least two weigh-ins to see a trend.</p>;
  const w = 420;
  const h = 140;
  const pad = 28;
  const values = points.map((p) => p[1]);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const xy = points.map(([, v], i) => [pad + (i / (points.length - 1)) * (w - pad * 2), h - pad - ((v - min) / span) * (h - pad * 2)] as const);
  const first = points[0]!;
  const last = points[points.length - 1]!;
  return (
    <svg className="chart" viewBox={`0 0 ${w} ${h + 16}`} role="img" aria-label={label}>
      <polyline points={xy.map(([x, y]) => `${x},${y}`).join(" ")} className="chart-line" fill="none" />
      {xy.map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r={3.5} className="chart-dot" />
      ))}
      <text x={pad} y={h + 10} className="chart-label">
        {first[0]} · {first[1]} {unit}
      </text>
      <text x={w - pad} y={h + 10} textAnchor="end" className="chart-label">
        {last[0]} · {last[1]} {unit}
      </text>
    </svg>
  );
}
