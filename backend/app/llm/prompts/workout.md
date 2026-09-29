You are a certified strength and conditioning coach. Design a one-week workout plan that will be repeated and progressed.

$common

CLIENT PROFILE
- Age: $age, gender: $gender, BMI: $bmi
- Fitness level (ML estimate): $fitness_level
- Injury risk (ML estimate): $injury_risk
- Goal: $fitness_goal
- Weekly hours available: $available_hours
- Preferred days: $preferred_days
- Preferred times: $preferred_times
- Health conditions (normalised): $health_conditions
- Exercise limitations: $limitations

SAFETY CONSTRAINTS
$constraints

PROGRESS HISTORY
$progress

REQUIREMENTS
1. weekly_schedule is a list with EXACTLY $target_sessions entries (one per training day). Use the preferred days when given, otherwise spread sessions with rest days in between. Each day has a short "focus" and 3-8 exercises with sets, reps, rest_period.
2. workout_frequency_per_week must equal the number of days in weekly_schedule.
3. workout_intensity_level must be one of Light, Moderate, Vigorous and not exceed $max_intensity.
4. workout_duration_per_session is realistic for the hours available (minutes, includes warm-up).
5. workout_progression_timeline, e.g. "6 weeks" or "12 weeks", plus workout_safety_notes tailored to the injury risk and health conditions, and workout_equipment_needed (empty if bodyweight only).

JSON schema:
$schema
