export type MethodologyBriefDto = {
  id: number
  name: string
  category: string | null
  scale_count: number
}

export type MethodologyBrief = {
  id: number
  name: string
  category: string | null
  scaleCount: number
}

export function mapMethodologyBrief(dto: MethodologyBriefDto): MethodologyBrief {
  return {
    id: dto.id,
    name: dto.name,
    category: dto.category,
    scaleCount: dto.scale_count,
  }
}
