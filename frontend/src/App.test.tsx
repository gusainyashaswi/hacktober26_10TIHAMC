import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import App from './App';

describe('App Shell', () => {
  it('renders the app shell and checks its title text', () => {
    render(<App />);
    const titleElement = screen.getByRole('heading', { level: 1 });
    expect(titleElement).toBeInTheDocument();
    expect(titleElement).toHaveTextContent('NoBluff');
  });
});
