import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { SettingsProvider } from "../state/settings";
import { SettingsPage } from "./SettingsPage";

const KEY = "AIzaSyExampleExampleExample12345";

describe("SettingsPage", () => {
  it("only shows the key field in live mode, masked by default", async () => {
    const u = userEvent.setup();
    render(
      <MemoryRouter>
        <SettingsProvider>
          <SettingsPage />
        </SettingsProvider>
      </MemoryRouter>,
    );
    expect(screen.queryByLabelText("Gemini API key")).not.toBeInTheDocument();
    await u.click(screen.getByRole("radio", { name: /Live/ }));
    expect(screen.getByLabelText("Gemini API key")).toHaveAttribute("type", "password");
    await u.click(screen.getByRole("button", { name: "Show" }));
    expect(screen.getByLabelText("Gemini API key")).toHaveAttribute("type", "text");
  });

  it("stores the key in sessionStorage only and can forget it", async () => {
    const u = userEvent.setup();
    render(
      <MemoryRouter>
        <SettingsProvider>
          <SettingsPage />
        </SettingsProvider>
      </MemoryRouter>,
    );
    await u.click(screen.getByRole("radio", { name: /Live/ }));
    await u.type(screen.getByLabelText("Gemini API key"), KEY);
    await u.click(screen.getByRole("button", { name: "Save for this tab" }));
    expect(sessionStorage.getItem("aetherfit.geminiKey")).toBe(KEY);
    expect(JSON.stringify({ ...localStorage })).not.toContain(KEY);
    await u.click(screen.getByRole("button", { name: "Forget key" }));
    expect(sessionStorage.getItem("aetherfit.geminiKey")).toBeNull();
    expect(screen.getByLabelText("Gemini API key")).toHaveValue("");
  });
});
