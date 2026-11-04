import "@testing-library/jest-dom/vitest";
import { cleanup, configure } from "@testing-library/react";
import { afterEach } from "vitest";

// waitFor() must still observe the asserted state; it may just take longer on a
// loaded runner. Explicit per-call timeouts in tests remain as strict as written.
configure({ asyncUtilTimeout: 3000 });

afterEach(() => {
  cleanup();
  localStorage.clear();
});
