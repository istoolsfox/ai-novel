import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { expect, test, vi } from 'vitest';
import { api, setToken, getToken } from '../api';
import { Login } from './Login';

test('登录成功后保存 token 并跳转工作台', async () => {
  vi.spyOn(api, 'accountLogin').mockResolvedValue({ token: 'tok-123', username: 'lyq', expires_at: '' });

  function LocationProbe() {
    const location = useLocation();
    return <span data-testid="loc">{location.pathname}</span>;
  }

  render(
    <MemoryRouter initialEntries={['/login']}>
      <Routes>
        <Route path="/login" element={<><Login /><LocationProbe /></>} />
        <Route path="/dashboard" element={<LocationProbe />} />
      </Routes>
    </MemoryRouter>,
  );

  fireEvent.change(screen.getByLabelText('用户名'), { target: { value: 'lyq' } });
  fireEvent.change(screen.getByLabelText('密码'), { target: { value: 'secret' } });
  fireEvent.click(screen.getByRole('button', { name: /登录/ }));

  await waitFor(() => expect(api.accountLogin).toHaveBeenCalledWith('lyq', 'secret'));
  await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/dashboard'));
  expect(getToken()).toBe('tok-123');
  setToken('');
});

test('密码错误时展示后端错误且不跳转', async () => {
  vi.spyOn(api, 'accountLogin').mockRejectedValue(new Error('用户名或密码不正确'));

  function LocationProbe() {
    const location = useLocation();
    return <span data-testid="loc">{location.pathname}</span>;
  }

  render(
    <MemoryRouter initialEntries={['/login']}>
      <Routes>
        <Route path="/login" element={<><Login /><LocationProbe /></>} />
      </Routes>
    </MemoryRouter>,
  );

  fireEvent.change(screen.getByLabelText('用户名'), { target: { value: 'lyq' } });
  fireEvent.change(screen.getByLabelText('密码'), { target: { value: 'wrong' } });
  fireEvent.click(screen.getByRole('button', { name: /登录/ }));

  expect(await screen.findByText('用户名或密码不正确')).toBeInTheDocument();
  expect(screen.getByTestId('loc').textContent).toBe('/login');
});
