import { useEffect, useState } from 'react'
import { fetchMethodologies } from '../api/methodologiesApi'
import type { MethodologyBrief } from '../types/methodology'

export type UseMethodologies = {
  methodologies: MethodologyBrief[]
  isLoading: boolean
  error: string | null
}

export function useMethodologies(): UseMethodologies {
  const [methodologies, setMethodologies] = useState<MethodologyBrief[]>([])
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    async function load(): Promise<void> {
      if (!active) return
      setIsLoading(true)
      setError(null)
      try {
        const list = await fetchMethodologies()
        if (!active) return
        setMethodologies(list)
      } catch {
        if (!active) return
        setError('Не удалось загрузить список методик.')
      } finally {
        if (active) setIsLoading(false)
      }
    }
    void load()
    return () => {
      active = false
    }
  }, [])

  return { methodologies, isLoading, error }
}
