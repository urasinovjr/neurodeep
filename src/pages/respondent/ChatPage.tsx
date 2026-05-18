import { useCallback, useEffect, useRef, useState } from 'react'
import { Button } from '../../shared/ui'
import { MIN_ANSWER_LENGTH, useChatFlow } from './hooks/useChatFlow'
import './chat.css'

const MAX_ANSWER_LENGTH = 4000

function autoResize(el: HTMLTextAreaElement | null): void {
  if (!el) return
  el.style.height = 'auto'
  el.style.height = `${el.scrollHeight}px`
}

function counterClass(length: number): string {
  if (length === 0) return 'chat-counter'
  if (length < MIN_ANSWER_LENGTH) return 'chat-counter is-warning'
  return 'chat-counter is-ready'
}

export default function ChatPage() {
  const flow = useChatFlow()
  const [text, setText] = useState<string>('')
  const textareaRef = useRef<HTMLTextAreaElement | null>(null)

  useEffect(() => {
    if (flow.currentQuestion && textareaRef.current) {
      autoResize(textareaRef.current)
    }
  }, [flow.currentQuestion])

  const handleSubmit = useCallback(async () => {
    if (text.length < MIN_ANSWER_LENGTH) return
    const sent = await flow.submit(text)
    if (sent) {
      setText('')
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto'
      }
    }
  }, [flow, text])

  if (flow.isLoadingState) {
    return (
      <main className="chat-page">
        <div className="chat-shell">
          <section className="chat-loading">Загрузка опроса…</section>
        </div>
      </main>
    )
  }

  if (flow.loadFailure) {
    return (
      <main className="chat-page">
        <div className="chat-shell">
          <section className="chat-failure">
            <p className="chat-failure-title">{flow.loadFailure.title}</p>
            <p className="chat-failure-detail">{flow.loadFailure.body}</p>
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                window.location.href = '/'
              }}
            >
              На главную
            </Button>
          </section>
        </div>
      </main>
    )
  }

  if (!flow.currentQuestion) {
    return (
      <main className="chat-page">
        <div className="chat-shell">
          <section className="chat-loading">Готовим следующий вопрос…</section>
        </div>
      </main>
    )
  }

  const questionLabel =
    flow.totalQuestions > 0
      ? `Вопрос ${flow.nextQuestionIndex + 1} из ${flow.totalQuestions}`
      : `Вопрос ${flow.nextQuestionIndex + 1}`
  const submitDisabled =
    text.length < MIN_ANSWER_LENGTH || flow.isProcessing

  return (
    <main className="chat-page">
      <div className="chat-shell">
        <section className="chat-progress">
          <div className="chat-progress-label">
            <span>{questionLabel}</span>
            <span>{flow.progressPercent}%</span>
          </div>
          <div className="chat-progress-bar">
            <div
              className="chat-progress-bar-fill"
              style={{ width: `${flow.progressPercent}%` }}
            />
          </div>
        </section>

        <section className="chat-question-card">
          <p className="chat-question-text">{flow.currentQuestion.text}</p>

          <textarea
            ref={textareaRef}
            className="chat-textarea"
            value={text}
            onChange={(event) => {
              setText(event.target.value)
              autoResize(event.currentTarget)
            }}
            placeholder="Напишите ваш ответ — не менее 10 символов"
            maxLength={MAX_ANSWER_LENGTH}
            disabled={flow.isProcessing}
            aria-label="Ответ на вопрос"
          />

          <div className="chat-meta-row">
            <span className={counterClass(text.length)}>
              {text.length} / {MAX_ANSWER_LENGTH} символов
              {text.length > 0 && text.length < MIN_ANSWER_LENGTH ? (
                <> · ещё {MIN_ANSWER_LENGTH - text.length} до отправки</>
              ) : null}
            </span>
            <Button
              type="button"
              variant="primary"
              onClick={() => void handleSubmit()}
              disabled={submitDisabled}
              isLoading={flow.isProcessing}
            >
              Отправить
            </Button>
          </div>

          {flow.submitError ? (
            <p className="chat-error">{flow.submitError}</p>
          ) : null}
        </section>
      </div>
    </main>
  )
}
