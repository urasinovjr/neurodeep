import { test, expect } from '@playwright/test'

test('private route /hr/dashboard redirects to /login when unauthenticated', async ({ page }) => {
  await page.route('**/api/auth/me', (route) => route.fulfill({ status: 401, body: '{}' }))
  await page.route('**/api/auth/refresh', (route) => route.fulfill({ status: 401, body: '{}' }))

  await page.goto('/hr/dashboard')

  await expect(page).toHaveURL(/\/login$/, { timeout: 15_000 })
})
