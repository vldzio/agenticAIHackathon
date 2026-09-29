import { FITNESS_LEVELS, INJURY_LEVELS, type Assessment } from "../api/types";
import { Badge, Notice } from "./Notice";
import { Drivers, LevelLadder, MacroBar, WeekGrid } from "./Viz";

const list = (items?: string[]) =>
  items && items.length > 0 ? (
    <ul className="bullets">
      {items.map((t, i) => (
        <li key={i}>{t}</li>
      ))}
    </ul>
  ) : null;

const injuryTone = (r: string) => (r.startsWith("Low") ? "good" : r.startsWith("Moderate") ? "warn" : "bad");

export function SafetyBanner({ a }: { a: Assessment }) {
  const s = a.safety;
  if (!s || s.level === "standard") return null;
  const clinician = s.level === "clinician_first";
  return (
    <Notice tone={clinician ? "danger" : "warn"} title={clinician ? "Please speak to a clinician before starting" : "This plan has been made more conservative"}>
      {list(s.reasons)}
      {s.requires_clearance && <p>Get medical clearance first, then follow this plan at the light intensity shown.</p>}
      <p className="muted">
        Limits applied: up to {s.max_sessions_per_week} sessions per week, {s.max_intensity.toLowerCase()} intensity.
      </p>
    </Notice>
  );
}

export function Overview({ a }: { a: Assessment }) {
  return (
    <div className="stack">
      <div className="grid grid-2">
        <section className="card" aria-labelledby="fit-h">
          <h3 id="fit-h">Fitness level</h3>
          {a.fitness ? (
            <>
              <p className="big">
                {a.fitness.level} <span className="muted small">{a.fitness.confidence.toFixed(0)}% confidence</span>
              </p>
              <LevelLadder levels={FITNESS_LEVELS} active={a.fitness.level} probabilities={a.fitness.probabilities as Record<string, number>} />
              {list(a.fitness.notes)}
              <Drivers drivers={a.fitness.drivers ?? []} />
            </>
          ) : (
            <p className="muted">Not available.</p>
          )}
        </section>
        <section className="card" aria-labelledby="inj-h">
          <h3 id="inj-h">Injury risk</h3>
          {a.injury ? (
            <>
              <p className="big">
                <Badge tone={injuryTone(a.injury.risk)}>{a.injury.risk}</Badge> <span className="muted small">{a.injury.confidence.toFixed(0)}% confidence</span>
              </p>
              <LevelLadder levels={INJURY_LEVELS} active={a.injury.risk} probabilities={a.injury.probabilities as Record<string, number>} tone="risk" />
              {a.injury.risk_factors && a.injury.risk_factors.length > 0 && (
                <>
                  <h4>Risk factors we noticed</h4>
                  {list(a.injury.risk_factors)}
                </>
              )}
              {list(a.injury.notes)}
              <Drivers drivers={a.injury.drivers ?? []} />
            </>
          ) : (
            <p className="muted">Not available.</p>
          )}
        </section>
      </div>

      {a.metrics && (
        <section className="card">
          <h3>Your numbers</h3>
          <dl className="facts">
            <div>
              <dt>BMI</dt>
              <dd>
                {a.metrics.bmi.toFixed(1)} <span className="muted">({a.metrics.bmi_category})</span>
              </dd>
            </div>
            <div>
              <dt>Age group</dt>
              <dd>{a.metrics.age_category}</dd>
            </div>
            {a.normalized && (
              <>
                <div>
                  <dt>Experience (as understood)</dt>
                  <dd>
                    {a.normalized.experience.experience_level} <span className="muted">· {a.normalized.experience.years_active} yrs</span>
                  </dd>
                </div>
                <div>
                  <dt>Weekly time (as understood)</dt>
                  <dd>{a.normalized.schedule.estimated_hours_per_week} h</dd>
                </div>
              </>
            )}
          </dl>
          {a.normalized?.health.conditions && a.normalized.health.conditions.length > 0 && (
            <p className="small">
              Health notes understood: <strong>{a.normalized.health.conditions.join(", ")}</strong>
            </p>
          )}
        </section>
      )}
    </div>
  );
}

export function Workout({ a }: { a: Assessment }) {
  const w = a.workout;
  if (!w) return <Notice tone="warn" title="No workout plan">This part of the plan could not be generated. Try creating the plan again.</Notice>;
  return (
    <div className="stack">
      <section className="card">
        <h3>Your week</h3>
        <WeekGrid days={w.weekly_schedule} />
        <dl className="facts">
          <div>
            <dt>Sessions / week</dt>
            <dd>{w.workout_frequency_per_week}</dd>
          </div>
          <div>
            <dt>Per session</dt>
            <dd>{w.workout_duration_per_session} min</dd>
          </div>
          <div>
            <dt>Intensity</dt>
            <dd>{w.workout_intensity_level}</dd>
          </div>
        </dl>
        {w.workout_progression_timeline && <p>{w.workout_progression_timeline}</p>}
        {w.workout_equipment_needed && w.workout_equipment_needed.length > 0 && (
          <p className="small">
            <strong>Equipment:</strong> {w.workout_equipment_needed.join(", ")}
          </p>
        )}
      </section>
      <div className="grid grid-2">
        {w.weekly_schedule.map((d) => (
          <section className="card" key={d.day} aria-label={`${d.day} workout`}>
            <h3>
              {d.day} <span className="muted small">· {d.focus}</span>
            </h3>
            <table className="table">
              <thead>
                <tr>
                  <th scope="col">Exercise</th>
                  <th scope="col">Sets</th>
                  <th scope="col">Reps</th>
                  <th scope="col">Rest</th>
                </tr>
              </thead>
              <tbody>
                {d.exercises.map((e, i) => (
                  <tr key={i}>
                    <td>
                      {e.exercise_name}
                      {e.notes && <div className="muted small">{e.notes}</div>}
                    </td>
                    <td>{e.sets}</td>
                    <td>{e.reps}</td>
                    <td>{e.rest_period}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        ))}
      </div>
      {w.workout_safety_notes && w.workout_safety_notes.length > 0 && (
        <section className="card">
          <h3>Safety notes</h3>
          {list(w.workout_safety_notes)}
        </section>
      )}
    </div>
  );
}

export function Nutrition({ a }: { a: Assessment }) {
  const n = a.nutrition;
  if (!n) return <Notice tone="warn" title="No nutrition plan">This part of the plan could not be generated. Try creating the plan again.</Notice>;
  const meals = n.meal_suggestions ?? [];
  return (
    <div className="stack">
      <section className="card">
        <h3>Daily targets</h3>
        <dl className="facts">
          <div>
            <dt>Target</dt>
            <dd className="big">{n.daily_calorie_target} kcal</dd>
          </div>
          <div>
            <dt>Maintenance (estimate)</dt>
            <dd>{n.maintenance_calories} kcal</dd>
          </div>
        </dl>
        <MacroBar protein={n.macro_targets.protein_g} carbs={n.macro_targets.carbs_g} fat={n.macro_targets.fat_g} />
        {list(n.notes)}
      </section>
      {meals.length === 0 ? (
        <Notice tone="warn" title="Meal ideas unavailable">Your calorie and macro targets are shown above, but meal suggestions could not be generated this time.</Notice>
      ) : (
        <div className="grid grid-2">
          {meals.map((m, i) => (
            <section className="card" key={i}>
              <h3>{m.meal_name}</h3>
              <p className="muted small">
                {Math.round(m.calories)} kcal · P {Math.round(m.protein_g)} g · C {Math.round(m.carbs_g)} g · F {Math.round(m.fat_g)} g
              </p>
              {list(m.foods)}
            </section>
          ))}
        </div>
      )}
      <section className="card">
        {n.hydration_recommendation && (
          <>
            <h3>Hydration</h3>
            <p>{n.hydration_recommendation}</p>
          </>
        )}
        {n.nutrition_timing_guidance && (
          <>
            <h3>Timing</h3>
            <p>{n.nutrition_timing_guidance}</p>
          </>
        )}
      </section>
    </div>
  );
}

export function Recovery({ a }: { a: Assessment }) {
  const r = a.recovery;
  if (!r) return <Notice tone="warn" title="No recovery plan">This part of the plan could not be generated. Try creating the plan again.</Notice>;
  const blocks: [string, string[] | undefined][] = [
    ["Recovery techniques", r.recovery_techniques],
    ["Rest-day activities", r.rest_day_activities],
    ["Mobility work", r.mobility_work],
    ["Stress management", r.stress_management_techniques],
    ["Building the habit", r.habit_formation_strategies],
    ["Staying consistent", r.adherence_tips],
    ["Making time", r.time_management_tips],
  ];
  return (
    <div className="stack">
      <div className="grid grid-2">
        <section className="card">
          <h3>Sleep</h3>
          <p className="big">{r.sleep_recommendations.hours_per_night} h / night</p>
          {list(r.sleep_recommendations.sleep_quality_tips)}
        </section>
        <section className="card">
          <h3>Fitting it in</h3>
          {r.schedule_integration.best_days && r.schedule_integration.best_days.length > 0 && (
            <p>
              <strong>Best days:</strong> {r.schedule_integration.best_days.join(", ")}
            </p>
          )}
          {r.schedule_integration.best_times && r.schedule_integration.best_times.length > 0 && (
            <p>
              <strong>Best times:</strong> {r.schedule_integration.best_times.join(", ")}
            </p>
          )}
          {r.schedule_integration.weekly_schedule_tips && <p>{r.schedule_integration.weekly_schedule_tips}</p>}
        </section>
        {blocks.map(([title, items]) =>
          items && items.length > 0 ? (
            <section className="card" key={title}>
              <h3>{title}</h3>
              {list(items)}
            </section>
          ) : null,
        )}
      </div>
      {r.deload_strategy && (
        <section className="card">
          <h3>Deload</h3>
          <p>{r.deload_strategy}</p>
        </section>
      )}
    </div>
  );
}
