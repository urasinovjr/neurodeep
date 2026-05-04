import { useState } from 'react'
import {
  Button,
  Input,
  Logo,
  Modal,
  ProgressBar,
  Spinner,
  Textarea,
  Toast,
} from '../../shared/ui'
import './home.css'

export default function HomePage() {
  const [name, setName] = useState('')
  const [bio, setBio] = useState('')
  const [progress, setProgress] = useState(35)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [toast, setToast] = useState<{ message: string; variant: 'success' | 'danger' } | null>(null)

  return (
    <main className="page-shell home-page">
      <div className="home-page__header">
        <Logo size="large" />
      </div>
      <p>Веб-платформа психологической диагностики через чат с NLP-анализом.</p>
      <p className="page-subtitle">Главная — каркас инициализирован, наполнение в TASK-061+.</p>

      <ul className="page-links">
        <li><a href="/login">Вход</a></li>
        <li><a href="/register">Регистрация</a></li>
        <li><a href="/hr/dashboard">HR-дашборд</a></li>
        <li><a href="/admin/methodologies">Методики (админ)</a></li>
      </ul>

      <section className="home-page__section">
        <h2 className="home-page__section-title">UI-кит</h2>

        <div className="home-page__row">
          <Button variant="primary" onClick={() => setToast({ message: 'Готово', variant: 'success' })}>
            Primary
          </Button>
          <Button variant="secondary">Secondary</Button>
          <Button variant="danger" onClick={() => setToast({ message: 'Что-то пошло не так', variant: 'danger' })}>
            Danger
          </Button>
          <Button variant="primary" isLoading>
            <Spinner size="small" /> Загрузка
          </Button>
          <Button variant="primary" disabled>Disabled</Button>
        </div>

        <div className="home-page__row home-page__row--col">
          <Input
            label="Имя"
            placeholder="Иван Иванов"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <Input
            label="Email"
            type="email"
            placeholder="user@example.com"
            error={name.length > 0 && name.length < 3 ? 'Минимум 3 символа' : undefined}
          />
          <Textarea
            label="О себе"
            placeholder="Несколько слов о себе…"
            rows={3}
            value={bio}
            onChange={(e) => setBio(e.target.value)}
          />
        </div>

        <div className="home-page__row home-page__row--col">
          <ProgressBar value={progress} label="Прогресс прохождения опроса" />
          <div className="home-page__row">
            <Button variant="secondary" size="medium" onClick={() => setProgress(Math.max(0, progress - 10))}>
              −10
            </Button>
            <Button variant="secondary" size="medium" onClick={() => setProgress(Math.min(100, progress + 10))}>
              +10
            </Button>
          </div>
        </div>

        <div className="home-page__row">
          <Spinner size="small" />
          <Spinner size="medium" />
          <Spinner size="large" />
        </div>

        <div className="home-page__row">
          <Button variant="primary" onClick={() => setIsModalOpen(true)}>
            Открыть модалку
          </Button>
        </div>
      </section>

      <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title="Заголовок модалки">
        <p>Содержимое модального окна. Закройте через × или клик по подложке.</p>
        <div className="home-page__row">
          <Button variant="primary" onClick={() => setIsModalOpen(false)}>OK</Button>
          <Button variant="secondary" onClick={() => setIsModalOpen(false)}>Отмена</Button>
        </div>
      </Modal>

      {toast && (
        <div className="home-page__toast-slot">
          <Toast
            message={toast.message}
            variant={toast.variant}
            onClose={() => setToast(null)}
          />
        </div>
      )}
    </main>
  )
}
