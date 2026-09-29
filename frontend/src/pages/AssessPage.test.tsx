import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../api/client";
import { SettingsProvider } from "../state/settings";
import { setApiKey, setMode } from "../lib/storage";
import { makeAssessment } from "../test/fixtures";
import { AssessPage } from "./AssessPage";

const streamCreate = vi.fn();
vi.mock("../api/client", async (orig) => ({ ...(await orig<typeof import("../api/client")>()), streamCreate: (...a: unknown[]) => streamCreate(...a) }));

const renderPage = () =>
  render(
    <MemoryRouter>
      <SettingsProvider>
        <Routes>
          <Route path="/" element={<AssessPage />} />
          <Route path="/plans/:id" element={<h1>Plan page</h1>} />
        </Routes>
      </SettingsProvider>
    </MemoryRouter>,
  );

async function fillValid() {
  const u = userEvent.setup();
  await u.type(screen.getByLabelText("Age"), "30");
  await u.type(screen.getByLabelText("Height (cm)"), "170");
  await u.type(screen.getByLabelText("Weight (kg)"), "70");
  await u.type(screen.getByLabelText("Your training history"), "Jogged for a year");
  await u.type(screen.getByLabelText("Time you can train"), "3 hours a week");
  return u;
}

describe("AssessPage", () => {
  beforeEach(() => {
    streamCreate.mockReset(); // braces: a returned function would be treated as a cleanup hook
  });

  it("blocks submission and shows inline errors for invalid input", async () => {
    const u = userEvent.setup();
    renderPage();
    await u.click(screen.getByRole("button", { name: "Generate my plan" }));
    expect(await screen.findByText("Age is required.")).toBeInTheDocument();
    expect(screen.getByLabelText("Age")).toHaveAttribute("aria-invalid", "true");
    expect(streamCreate).not.toHaveBeenCalled();
  });

  it("rejects an out-of-range age", async () => {
    const u = userEvent.setup();
    renderPage();
    await u.type(screen.getByLabelText("Age"), "5");
    await u.click(screen.getByRole("button", { name: "Generate my plan" }));
    expect(await screen.findByText("Age must be between 18 and 100.")).toBeInTheDocument();
  });

  it("streams progress and navigates to the plan", async () => {
    streamCreate.mockImplementation(async (_p: unknown, _m: unknown, onEvent: (e: unknown) => void) => {
      onEvent({ event: "node", node: "form_parser", label: "x", status: "ok" });
      return makeAssessment();
    });
    renderPage();
    const u = await fillValid();
    await u.click(screen.getByRole("button", { name: "Generate my plan" }));
    expect(await screen.findByRole("heading", { name: "Plan page" })).toBeInTheDocument();
    const [profile, mode] = streamCreate.mock.calls[0]!;
    expect(mode).toBe("mock");
    expect(profile).toMatchObject({ age: 30, height_cm: 170, weight_kg: 70, health_conditions: "None" });
  });

  it("shows API failures with a retry", async () => {
    streamCreate.mockRejectedValue(new ApiError(429, "llm_rate_limited", "quota"));
    renderPage();
    const u = await fillValid();
    await u.click(screen.getByRole("button", { name: "Generate my plan" }));
    expect(await screen.findByText("Gemini quota reached")).toBeInTheDocument();
    streamCreate.mockResolvedValue(makeAssessment());
    await u.click(screen.getByRole("button", { name: "Try again" }));
    await waitFor(() => expect(screen.getByRole("heading", { name: "Plan page" })).toBeInTheDocument());
  });

  it("maps server field errors back onto the form", async () => {
    streamCreate.mockRejectedValue(new ApiError(422, "validation_error", "Invalid", [{ field: "profile.weight_kg", message: "server says no" }]));
    renderPage();
    const u = await fillValid();
    await u.click(screen.getByRole("button", { name: "Generate my plan" }));
    expect(await screen.findByText("server says no")).toBeInTheDocument();
  });

  it("disables the form in live mode until a key is present", () => {
    setMode("live");
    renderPage();
    expect(screen.getByText("Add your Gemini API key")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Generate my plan" })).toBeDisabled();
  });

  it("enables the form in live mode once a key is saved", () => {
    setMode("live");
    setApiKey("AIzaSyExampleExampleExample12345");
    renderPage();
    expect(screen.getByRole("button", { name: "Generate my plan" })).toBeEnabled();
  });
});
