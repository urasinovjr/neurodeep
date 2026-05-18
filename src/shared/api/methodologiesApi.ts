import { apiClient } from './client'
import {
  mapMethodologyBrief,
  type MethodologyBrief,
  type MethodologyBriefDto,
} from '../types/methodology'

export async function fetchMethodologies(): Promise<MethodologyBrief[]> {
  const list = await apiClient.get<MethodologyBriefDto[]>('/methodologies')
  return list.map(mapMethodologyBrief)
}
