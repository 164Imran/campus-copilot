import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { AppRoutes } from './App';

test('renders desktop shell', () => {
  render(
    <MemoryRouter initialEntries={['/os']}>
      <AppRoutes />
    </MemoryRouter>
  );
  const main = screen.getByRole('main');
  expect(main).toHaveClass('desktop');
  expect(screen.getByText('TUM OS')).toBeInTheDocument();
});
