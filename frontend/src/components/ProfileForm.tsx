import { useState, type ReactNode } from "react";
import { GENDERS, GOALS } from "../api/types";
import { EMPTY_DRAFT, LIMITS, toProfile, validateDraft, type DraftErrors, type ProfileDraft } from "../lib/validation";
import type { ProfileIn } from "../api/types";

function Field({ id, label, hint, error, children }: { id: string; label: string; hint?: string; error?: string; children: ReactNode }) {
  return (
    <div className={`field ${error ? "field-invalid" : ""}`}>
      <label htmlFor={id}>{label}</label>
      {children}
      {hint && !error && (
        <p className="hint" id={`${id}-hint`}>
          {hint}
        </p>
      )}
      {error && (
        <p className="field-error" id={`${id}-error`} role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

export function ProfileForm({
  onSubmit,
  disabled,
  submitLabel = "Generate my plan",
  serverErrors,
  initial = EMPTY_DRAFT,
}: {
  onSubmit: (p: ProfileIn) => void;
  disabled?: boolean;
  submitLabel?: string;
  serverErrors?: DraftErrors;
  initial?: ProfileDraft;
}) {
  const [draft, setDraft] = useState<ProfileDraft>(initial);
  const [errors, setErrors] = useState<DraftErrors>({});
  const shown = { ...serverErrors, ...errors };

  const set = <K extends keyof ProfileDraft>(k: K, v: ProfileDraft[K]) => {
    setDraft((d) => ({ ...d, [k]: v }));
    setErrors((e) => ({ ...e, [k]: undefined }));
  };
  const bind = (k: keyof ProfileDraft) => ({
    id: k,
    "aria-invalid": shown[k] ? true : undefined,
    "aria-describedby": shown[k] ? `${k}-error` : `${k}-hint`,
  });

  return (
    <form
      className="form"
      noValidate
      onSubmit={(e) => {
        e.preventDefault();
        const found = validateDraft(draft);
        setErrors(found);
        if (Object.keys(found).length === 0) onSubmit(toProfile(draft));
        else document.getElementById(Object.keys(found)[0] as string)?.focus();
      }}
    >
      <fieldset disabled={disabled}>
        <legend>About you</legend>
        <div className="grid grid-2">
          <Field id="user_name" label="Name (optional)" error={shown.user_name}>
            <input {...bind("user_name")} value={draft.user_name} maxLength={LIMITS.user_name} onChange={(e) => set("user_name", e.target.value)} autoComplete="given-name" />
          </Field>
          <Field id="gender" label="Gender" hint="Used by the prediction models.">
            <select {...bind("gender")} value={draft.gender} onChange={(e) => set("gender", e.target.value as ProfileDraft["gender"])}>
              {GENDERS.map((g) => (
                <option key={g}>{g}</option>
              ))}
            </select>
          </Field>
          <Field id="age" label="Age" error={shown.age} hint={`${LIMITS.age.min}–${LIMITS.age.max} years`}>
            <input {...bind("age")} inputMode="numeric" value={draft.age} onChange={(e) => set("age", e.target.value)} />
          </Field>
          <Field id="height_cm" label="Height (cm)" error={shown.height_cm}>
            <input {...bind("height_cm")} inputMode="decimal" value={draft.height_cm} onChange={(e) => set("height_cm", e.target.value)} />
          </Field>
          <Field id="weight_kg" label="Weight (kg)" error={shown.weight_kg}>
            <input {...bind("weight_kg")} inputMode="decimal" value={draft.weight_kg} onChange={(e) => set("weight_kg", e.target.value)} />
          </Field>
          <Field id="fitness_goal" label="Main goal">
            <select {...bind("fitness_goal")} value={draft.fitness_goal} onChange={(e) => set("fitness_goal", e.target.value as ProfileDraft["fitness_goal"])}>
              {GOALS.map((g) => (
                <option key={g}>{g}</option>
              ))}
            </select>
          </Field>
        </div>
      </fieldset>

      <fieldset disabled={disabled}>
        <legend>Training & health</legend>
        <Field
          id="fitness_experience"
          label="Your training history"
          error={shown.fitness_experience}
          hint="In your own words, e.g. “I jogged a few times a week for 2 years, nothing since 2023”."
        >
          <textarea {...bind("fitness_experience")} rows={3} value={draft.fitness_experience} onChange={(e) => set("fitness_experience", e.target.value)} />
        </Field>
        <Field
          id="available_hours_per_week"
          label="Time you can train"
          error={shown.available_hours_per_week}
          hint="e.g. “4–5 hours a week, weekday mornings” or “45 minutes, 3 times a week”."
        >
          <textarea {...bind("available_hours_per_week")} rows={2} value={draft.available_hours_per_week} onChange={(e) => set("available_hours_per_week", e.target.value)} />
        </Field>
        <Field
          id="health_conditions"
          label="Health conditions or injuries (optional)"
          error={shown.health_conditions}
          hint="e.g. “mild asthma, sore left knee”. Leave blank if none."
        >
          <textarea {...bind("health_conditions")} rows={2} value={draft.health_conditions} onChange={(e) => set("health_conditions", e.target.value)} />
        </Field>
        <label className="check">
          <input type="checkbox" checked={draft.previous_injury} onChange={(e) => set("previous_injury", e.target.checked)} />
          <span>I have had a training-related injury in the past</span>
        </label>
      </fieldset>

      <button className="btn btn-primary" type="submit" disabled={disabled}>
        {submitLabel}
      </button>
    </form>
  );
}
