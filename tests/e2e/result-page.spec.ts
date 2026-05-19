import { test, expect } from '@playwright/test'

const SESSION_ID = '11111111-2222-3333-4444-555555555555'

const RESULT_PAYLOAD = {
  session_id: SESSION_ID,
  status: 'completed',
  completed_at: '2026-05-18T10:00:00Z',
  scores: [],
  profile_text: null,
  pinaba_url: null,
  scale_scores: [
    { scale_id: 1, scale_name: 'Эмоции', value: 78, level: 'high', fragment: '' },
    { scale_id: 2, scale_name: 'Мышление', value: 52, level: 'mid', fragment: '' },
    { scale_id: 3, scale_name: 'Тело', value: 24, level: 'low', fragment: '' },
  ],
  text_interpretation: 'Развёрнутая интерпретация профиля респондента.',
  recommendations: ['Первая рекомендация.', 'Вторая рекомендация.'],
  wheel_balance: {
    emotions: 78,
    thinking: 52,
    body: 24,
    relationships: 60,
    meaning: 50,
  },
}

test('result page renders interpretation, recommendations and download buttons', async ({ page }) => {
  await page.route(`**/api/surveys/sessions/${SESSION_ID}/result`, (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(RESULT_PAYLOAD),
    }),
  )

  await page.goto(`/chat/${SESSION_ID}/result`)

  await expect(page.getByText('Развёрнутая интерпретация профиля респондента.')).toBeVisible()
  await expect(page.getByText('Первая рекомендация.')).toBeVisible()
  await expect(page.getByText('Вторая рекомендация.')).toBeVisible()
  await expect(page.getByRole('link', { name: /pdf|скачать pdf/i })).toBeVisible()
})
