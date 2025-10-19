import { useMemo } from "react";
import type { AppEnvironment } from "../config/env";
import { env } from "../config/env";

export const useEnvironment = (): AppEnvironment => useMemo(() => env, []);

