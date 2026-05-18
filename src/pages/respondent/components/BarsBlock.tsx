import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type {
  ScaleLevel,
  ScaleScoreBreakdown,
} from '../api/respondent.mapper'

const LEVEL_COLOR: Record<ScaleLevel, string> = {
  low: '#22C55E',
  mid: '#F59E0B',
  high: '#EF4444',
}

const LEVEL_LABEL: Record<ScaleLevel, string> = {
  low: 'низкий',
  mid: 'средний',
  high: 'высокий',
}

type Props = {
  scales: ScaleScoreBreakdown[]
}

export default function BarsBlock({ scales }: Props) {
  if (scales.length === 0) {
    return <div className="result-empty">Нет данных по шкалам.</div>
  }
  const data = scales.map((s) => ({
    name: s.scaleName,
    value: Math.round(s.value),
    level: s.level,
  }))
  const height = Math.max(180, data.length * 44)
  return (
    <div className="result-chart-wrap" data-testid="bars-block">
      <ResponsiveContainer width="100%" height={height}>
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 10, right: 24, bottom: 10, left: 8 }}
        >
          <XAxis
            type="number"
            domain={[0, 100]}
            tick={{ fontSize: 11, fill: '#94A3B8' }}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            type="category"
            dataKey="name"
            tick={{ fontSize: 12, fill: '#0F172A' }}
            tickLine={false}
            axisLine={false}
            width={140}
          />
          <Tooltip
            cursor={{ fill: 'rgba(82, 96, 255, 0.08)' }}
            formatter={(value: number, _name: string, payload: { payload?: { level?: ScaleLevel } }) => {
              const level = payload?.payload?.level
              const levelLabel = level ? LEVEL_LABEL[level] : ''
              return [`${value} / 100`, `Уровень: ${levelLabel}`]
            }}
          />
          <Bar dataKey="value" radius={[6, 6, 6, 6]} barSize={18}>
            {data.map((entry, index) => (
              <Cell key={index} fill={LEVEL_COLOR[entry.level]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
