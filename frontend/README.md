# NoBluff Frontend

Web interface for NoBluff, an evidence-based investigation tool for open-source issues and pull requests. Built with React, TypeScript, and Vite.

## Requirements

- Node.js >= 18
- npm >= 9

## Getting Started

### Install Dependencies

```bash
cd frontend
npm install
```

Or for reproducible CI installations:

```bash
cd frontend
npm ci
```

### Development Server

Start the local development server with Hot Module Replacement (HMR):

```bash
npm run dev
```

### Type Checking

Run TypeScript type check without emitting files:

```bash
npm run typecheck
```

### Running Tests

Execute unit and integration tests using Vitest and React Testing Library:

```bash
npm run test
```

Or run Vitest explicitly in run mode:

```bash
npm run test -- --run
```

### Production Build

Build and bundle optimized static production assets to `dist/`:

```bash
npm run build
```
