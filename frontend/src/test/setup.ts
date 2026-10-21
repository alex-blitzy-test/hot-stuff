import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

// React Testing Library only registers its automatic cleanup when a global
// `afterEach` exists, and this project's Vitest config leaves `globals` off,
// so cleanup is registered explicitly here.
afterEach(() => {
  cleanup();
});
