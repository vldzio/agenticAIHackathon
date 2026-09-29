import type { components } from "./schema";

type S = components["schemas"];

export type Assessment = S["Assessment"];
export type AssessmentSummary = S["AssessmentSummary"];
export type ProfileIn = S["ProfileIn"];
export type ProgressLogIn = S["ProgressLogIn"];
export type ProgressLogOut = S["ProgressLogOut"];
export type ProgressSummary = S["ProgressSummary"];
export type WorkoutPlan = S["WorkoutPlan"];
export type WorkoutDay = S["WorkoutDay"];
export type NutritionPlan = S["NutritionPlan"];
export type RecoveryPlan = S["RecoveryPlan"];
export type SafetyResult = S["SafetyResult"];
export type FitnessResult = S["FitnessResult"];
export type InjuryResult = S["InjuryResult"];
export type NodeError = S["NodeError"];
export type Driver = S["Driver"];
export type Health = S["Health"];

export type Mode = "mock" | "live";
export type SectionStatus = "ok" | "partial" | "failed" | "skipped";

export const FITNESS_LEVELS = ["Beginner", "Intermediate", "Advanced", "Athlete"] as const;
export const INJURY_LEVELS = ["Low Risk", "Moderate Risk", "High Risk", "Very High Risk"] as const;
export const WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"] as const;
export const GOALS: ProfileIn["fitness_goal"][] = ["Weight Loss", "Muscle Building", "Endurance/Cardio", "General Fitness"];
export const GENDERS: ProfileIn["gender"][] = ["Male", "Female", "Other"];

export interface ModelInfo {
  trained_at: string;
  environment: Record<string, string>;
  models: Record<
    string,
    {
      classes: string[];
      global_feature_importance: Record<string, number>;
      cross_validation: { folds: number; accuracy_mean: number; accuracy_std: number };
      training_evaluation: Metric;
      data: { provenance: string; training_file: string };
      artifact_bytes: number;
    }
  >;
  guardrails: string[];
  limitations: string[];
}

export interface Metric {
  samples: number;
  accuracy: number;
  macro_f1: number;
  within_one_class_accuracy: number;
  log_loss: number;
  expected_calibration_error: number;
  classes: string[];
  precision_per_class: Record<string, number>;
}

export interface ModelEvaluation {
  source: "live" | "stored";
  models: Record<string, Metric>;
}

export interface WorkflowNode {
  name: string;
  label: string;
  section: string;
}

export type StreamEvent =
  | { event: "start"; nodes: WorkflowNode[] }
  | { event: "node"; node: string; label: string; status: SectionStatus }
  | { event: "result"; assessment: Assessment }
  | { event: "error"; code: string; message: string; status: number };
