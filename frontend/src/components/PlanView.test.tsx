import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { PlanView } from "../pages/ResultPage";
import { makeAssessment } from "../test/fixtures";
import type { Assessment } from "../api/types";

const renderPlan = (a: Assessment) =>
  render(
    <MemoryRouter>
      <PlanView a={a} />
    </MemoryRouter>,
  );

describe("PlanView", () => {
  it("labels simulated plans and shows predictions", () => {
    renderPlan(makeAssessment());
    expect(screen.getByText("Simulated plan")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Fitness level" })).toBeInTheDocument();
    expect(screen.getByText(/61% confidence/)).toBeInTheDocument();
    expect(screen.getAllByText("Moderate Risk").length).toBeGreaterThan(0);
    // the API sends probabilities as 0-1 fractions; the UI must show percentages
    expect(screen.getByRole("img", { name: "Intermediate: 61 percent" })).toBeInTheDocument();
  });

  it("does not claim a live plan is simulated", () => {
    renderPlan(makeAssessment({ simulated: false, mode: "live" }));
    expect(screen.queryByText("Simulated plan")).not.toBeInTheDocument();
  });

  it("shows a prominent clinician-first warning", () => {
    renderPlan(
      makeAssessment({
        safety: {
          level: "clinician_first",
          max_intensity: "Light",
          max_sessions_per_week: 3,
          requires_clearance: true,
          reasons: ["Reported chest pain during exercise"],
          constraints: [],
          disclaimer: "Educational only.",
        },
      }),
    );
    expect(screen.getByRole("alert")).toHaveTextContent(/speak to a clinician/i);
    expect(screen.getByText(/chest pain/)).toBeInTheDocument();
  });

  it("surfaces partial results instead of hiding failures", () => {
    renderPlan(
      makeAssessment({
        status: "partial",
        nutrition: null,
        sections: { fitness: "ok", nutrition: "failed" },
        errors: [{ node: "nutrition_advisor", code: "llm_error", message: "Nutrition generation failed", retryable: true }],
      }),
    );
    expect(screen.getByText("Some parts of this plan are missing")).toBeInTheDocument();
    expect(screen.getByText("Nutrition generation failed")).toBeInTheDocument();
  });

  it("switches between tabs", async () => {
    renderPlan(makeAssessment());
    await userEvent.click(screen.getByRole("tab", { name: "Workout" }));
    expect(screen.getByText("Goblet squat")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("tab", { name: "Nutrition" }));
    expect(screen.getByText("1800 kcal")).toBeInTheDocument();
    expect(screen.getByText("Idli")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("tab", { name: "Recovery" }));
    expect(screen.getByText("8 h / night")).toBeInTheDocument();
  });

  it("explains a missing nutrition plan on its tab", async () => {
    renderPlan(makeAssessment({ nutrition: null }));
    await userEvent.click(screen.getByRole("tab", { name: "Nutrition" }));
    expect(screen.getByText("No nutrition plan")).toBeInTheDocument();
  });
});
