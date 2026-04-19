import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { AppRoutes } from './App';

test('renders lock screen at /', () => {
  render(
    <MemoryRouter initialEntries={['/']}>
      <AppRoutes />
    </MemoryRouter>
  );
  const main = screen.getByRole('main');
  expect(main).toHaveClass('landing');
  expect(screen.getAllByText('TUM OS').length).toBeGreaterThanOrEqual(1);
  expect(screen.getByText(/Welcome to TUM/)).toBeInTheDocument();
  expect(
    screen.getByRole('button', { name: /login/i, hidden: true })
  ).toBeInTheDocument();
});

test('renders desktop shell at /desktop', () => {
  render(
    <MemoryRouter initialEntries={['/desktop']}>
      <AppRoutes />
    </MemoryRouter>
  );
  const main = screen.getByRole('main');
  expect(main).toHaveClass('desktop');
  expect(screen.getByText('TUM OS')).toBeInTheDocument();
});
