import React from 'react';
import { render, screen } from '@testing-library/react';
import App from './App';

test('renders desktop shell', () => {
  render(<App />);
  const main = screen.getByRole('main');
  expect(main).toHaveClass('desktop');
  expect(screen.getByText('TUM OS')).toBeInTheDocument();
});
