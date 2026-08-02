"use client";

import { RotateCcw, TriangleAlert } from "lucide-react";
import { useEffect } from "react";

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <main className="route-error">
      <TriangleAlert aria-hidden="true" size={30} />
      <h1>The verification workspace could not load</h1>
      <p>Your content has not been submitted. Reload this view and try again.</p>
      <button type="button" onClick={reset}>
        <RotateCcw aria-hidden="true" size={16} />
        Reload workspace
      </button>
    </main>
  );
}
