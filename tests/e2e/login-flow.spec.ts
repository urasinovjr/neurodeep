import { test, expect } from '@playwright/test'

const RESEARCHER_USER = {
  id: 1,
  email: 'hr@example.com',
  first_name: 'Анна',
  last_name: 'Петрова',
  role: 'researcher',
  status: 'active',
  email_verified: true,
}

test('successful login redirects researcher to /hr/dashboard', async ({ page }) => {
  await page.route('**/api/auth/login', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      headers: { 'X-CSRF-Token': 'mock-csrf' },
      body: JSON.stringify({ access_token: 'mock.jwt.token', csrf_token: 'mock-csrf' }),
    }),
  )
  await page.route('**/api/auth/me', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(RESEARCHER_USER),
    }),
  )
  await page.route('**/api/surveys**', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ items: [], total: 0, limit: 12, offset: 0 }),
    }),
  )
  await page.route('**/api/methodologies', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    }),
  )

  await page.goto('/login')
  await page.getByLabel(/email|почт/i).fill('hr@example.com')
  await page.getByLabel(/паро/i).fill('Password123!')
  await page.getByRole('button', { name: /войти|вход/i }).click()

  await page.waitForURL('**/hr/dashboard', { timeout: 10_000 })
  await expect(page).toHaveURL(/\/hr\/dashboard$/)
  await expect(page.getByRole('heading', { name: /мои исследования/i })).toBeVisible()
})
