'use client';

import { useState } from 'react';

export default function SignupPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [error, setError] = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    // Better Auth's signup endpoint; email verification is required before
    // first generation (tenancy-and-data.md: "Email verification before
    // anything expensive"). In the local/dev path, signup returns a session
    // directly; the page then routes to the editor.
    const res = await fetch('/api/auth/sign-up/email', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, password }),
    });
    if (!res.ok) {
      const data = (await res.json().catch(() => ({}))) as { message?: string };
      setError(
        data.message ??
          'Signup failed — the response is identical for existing addresses (enumeration-safe).',
      );
      return;
    }
    window.location.href = '/';
  }

  return (
    <form onSubmit={handleSubmit} className="auth-form">
      <h1>Sign up</h1>
      <label>
        Name
        <input value={name} onChange={(e) => setName(e.target.value)} required />
      </label>
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
          minLength={8}
          required
        />
      </label>
      {error && <p className="auth-error">{error}</p>}
      <button type="submit">Create account</button>
      <p>
        Already have an account? <a href="/login">Log in</a>
      </p>
    </form>
  );
}
