import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import type { WheelBalance } from '../api/respondent.mapper'

const DOMAIN_LABELS: Record<keyof WheelBalance, string> = {
  emotions: 'Эмоции',
  thinking: 'Мышление',
  body: 'Тело',
  relationships: 'Отношения',
  meaning: 'Смыслы',
}

const DOMAIN_COLORS: string[] = [
  '#5260FF',
  '#8B5CF6',
  '#EC4899',
  '#22C55E',
  '#F59E0B',
]

type Props = {
  wheel: WheelBalance
}

export default function WheelBlock({ wheel }: Props) {
  const entries = (
    Object.entries(wheel) as Array<[keyof WheelBalance, number]>
  ).map(([key, value]) => ({
    name: DOMAIN_LABELS[key],
    value: Math.max(0, value),
  }))
  const isEmpty = entries.every((entry) => entry.value === 0)
  if (isEmpty) {
    return (
      <div className="result-empty">
        Колесо баланса появится после расчёта значений по шкалам.
      </div>
    )
  }
  return (
    <div className="result-chart-wrap" data-testid="wheel-block">
      <ResponsiveContainer width="100%" aspect={1}>
        <PieChart>
          <Tooltip
            formatter={(value: number) => [`${Math.round(value)} / 100`, 'Среднее']}
          />
          <Pie
            data={entries}
            dataKey="value"
            innerRadius="35%"
            outerRadius="78%"
            stroke="#FFFFFF"
            strokeWidth={2}
            label={(entry: { name?: string; value?: number }) => {
              const name = entry.name ?? ''
              const value = entry.value ?? 0
              return `${name} · ${Math.round(value)}`
            }}
            isAnimationActive
          >
            {entries.map((_, index) => (
              <Cell
                key={index}
                fill={DOMAIN_COLORS[index % DOMAIN_COLORS.length]}
              />
            ))}
          </Pie>
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}
