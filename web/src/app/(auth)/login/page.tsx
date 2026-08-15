'use client';

import { useState } from 'react';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    const res = await fetch('/api/auth/sign-in/email', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const data = (await res.json().catch(() => ({}))) as { message?: string };
      setError(
        data.message ??
          'Login failed — the response is identical for existing addresses (enumeration-safe).',
      );
      return;
    }
    window.location.href = '/';
  }

  return (
    <form onSubmit={handleSubmit} className="auth-form">
      <h1>Log in</h1>
      <label>
        Email
        <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
      </label>
      <label>
        Password
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
      </label>
      {error && <p className="auth-error">{error}</p>}
      <button type="submit">Log in</button>
      <p>
        New here? <a href="/signup">Sign up</a>
      </p>
    </form>
  );
}
