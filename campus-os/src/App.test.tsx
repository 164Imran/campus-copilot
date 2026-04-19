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
  expect(screen.getByText('TUM OS')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /login/i })).toBeInTheDocument();
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
