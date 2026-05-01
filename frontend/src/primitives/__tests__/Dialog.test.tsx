// @vitest-environment jsdom
/**
 * Unit tests for the Dialog primitive (issue #371).
 *
 * Covers:
 * 1. Renders nothing when open=false.
 * 2. Renders dialog with correct ARIA roles when open=true.
 * 3. Escape key closes the dialog.
 * 4. Clicking the overlay closes the dialog (closeOnOverlayClick=true default).
 * 5. Clicking the overlay does NOT close when closeOnOverlayClick=false.
 * 6. DialogClose button calls onClose.
 * 7. Renders all sub-components (DialogTitle, DialogContent, DialogActions).
 */
import "@testing-library/jest-dom/vitest";
import React from "react";
import { cleanup, render, screen, fireEvent } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  DialogClose,
} from "../Dialog";

afterEach(cleanup);

// Suppress React DOM warnings about unsupported `inert` attribute in jsdom
beforeEach(() => {
  vi.spyOn(console, "error").mockImplementation(() => {});
});
afterEach(() => {
  vi.restoreAllMocks();
});

function renderDialog(
  props: Partial<React.ComponentProps<typeof Dialog>> = {},
  children?: React.ReactNode,
) {
  const onClose = props.onClose ?? vi.fn();
  render(
    <Dialog open={props.open ?? true} onClose={onClose} {...props}>
      {children ?? (
        <>
          <DialogTitle>Test dialog</DialogTitle>
          <DialogContent>Content here</DialogContent>
          <DialogActions>
            <DialogClose>Close</DialogClose>
          </DialogActions>
        </>
      )}
    </Dialog>,
  );
  return { onClose };
}

describe("Dialog", () => {
  it("renders nothing when closed", () => {
    const { container } = render(
      <Dialog open={false} onClose={vi.fn()}>
        <DialogTitle>Hidden</DialogTitle>
      </Dialog>,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders with role=dialog and aria-modal when open", () => {
    renderDialog();
    const dialog = screen.getByRole("dialog");
    expect(dialog).toBeTruthy();
    expect(dialog.getAttribute("aria-modal")).toBe("true");
  });

  it("has aria-labelledby pointing at the title", () => {
    renderDialog();
    const dialog = screen.getByRole("dialog");
    const labelledBy = dialog.getAttribute("aria-labelledby");
    expect(labelledBy).toBeTruthy();
    const titleEl = document.getElementById(labelledBy!);
    expect(titleEl?.textContent).toBe("Test dialog");
  });

  it("calls onClose when Escape is pressed", () => {
    const { onClose } = renderDialog();
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when overlay is clicked (default)", () => {
    const { onClose } = renderDialog();
    // The overlay is the element with aria-hidden="true" that precedes the panel
    const overlay = document.querySelector("[aria-hidden='true']") as HTMLElement;
    expect(overlay).toBeTruthy();
    fireEvent.click(overlay);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("does NOT call onClose when overlay clicked and closeOnOverlayClick=false", () => {
    const { onClose } = renderDialog({ closeOnOverlayClick: false });
    const overlay = document.querySelector("[aria-hidden='true']") as HTMLElement;
    if (overlay) fireEvent.click(overlay);
    expect(onClose).not.toHaveBeenCalled();
  });

  it("DialogClose button calls onClose", () => {
    const { onClose } = renderDialog();
    const closeBtn = screen.getByRole("button", { name: /close/i });
    fireEvent.click(closeBtn);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("renders DialogTitle, DialogContent and DialogActions children", () => {
    renderDialog();
    expect(screen.getByText("Test dialog")).toBeTruthy();
    expect(screen.getByText("Content here")).toBeTruthy();
    expect(screen.getByRole("button", { name: /close/i })).toBeTruthy();
  });
});
