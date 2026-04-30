import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { Skeleton } from "../Skeleton";

describe("Skeleton", () => {
  beforeEach(() => {
    // Default: prefers-reduced-motion is NOT set
    window.matchMedia = vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));
  });

  it("renders a single bar by default with status role", () => {
    render(<Skeleton aria-label="Loading content" />);
    const root = screen.getByRole("status");
    expect(root).toBeInTheDocument();
    expect(root).toHaveAttribute("aria-label", "Loading content");
    expect(root).toHaveAttribute("aria-busy", "true");
  });

  it("applies width and height styles to the bar", () => {
    const { container } = render(
      <Skeleton width={200} height={32} aria-label="Loading widget" />,
    );
    const bar = container.querySelector(".skeleton-bar") as HTMLElement;
    expect(bar).toBeTruthy();
    expect(bar.style.width).toBe("200px");
    expect(bar.style.height).toBe("32px");
  });

  it("accepts string width and height (CSS units passed through)", () => {
    const { container } = render(
      <Skeleton width="50%" height="2em" aria-label="Loading flex" />,
    );
    const bar = container.querySelector(".skeleton-bar") as HTMLElement;
    expect(bar.style.width).toBe("50%");
    expect(bar.style.height).toBe("2em");
  });

  it("applies a custom radius", () => {
    const { container } = render(
      <Skeleton radius={12} aria-label="Loading rounded" />,
    );
    const bar = container.querySelector(".skeleton-bar") as HTMLElement;
    expect(bar.style.borderRadius).toBe("12px");
  });

  it("renders N child bars when lines prop is provided", () => {
    const { container } = render(
      <Skeleton lines={4} aria-label="Loading paragraph" />,
    );
    const bars = container.querySelectorAll(".skeleton-bar");
    expect(bars.length).toBe(4);
  });

  it("renders a single bar when lines is 1", () => {
    const { container } = render(
      <Skeleton lines={1} aria-label="Loading single line" />,
    );
    const bars = container.querySelectorAll(".skeleton-bar");
    expect(bars.length).toBe(1);
  });

  it("honors aria-label for accessibility", () => {
    render(<Skeleton aria-label="Fleet data is loading" />);
    expect(screen.getByLabelText("Fleet data is loading")).toBeInTheDocument();
  });

  it("uses a default aria-label when none provided", () => {
    render(<Skeleton />);
    const root = screen.getByRole("status");
    expect(root).toHaveAttribute("aria-label", "Loading");
  });

  it("does NOT add reduced-motion class when motion is allowed", () => {
    const { container } = render(<Skeleton aria-label="Loading" />);
    const root = container.querySelector(".skeleton") as HTMLElement;
    expect(root.classList.contains("skeleton-reduced-motion")).toBe(false);
  });

  it("adds reduced-motion class when prefers-reduced-motion: reduce", () => {
    window.matchMedia = vi.fn().mockImplementation((query: string) => ({
      matches: query === "(prefers-reduced-motion: reduce)",
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));

    const { container } = render(<Skeleton aria-label="Loading reduced" />);
    const root = container.querySelector(".skeleton") as HTMLElement;
    expect(root.classList.contains("skeleton-reduced-motion")).toBe(true);
  });
});
