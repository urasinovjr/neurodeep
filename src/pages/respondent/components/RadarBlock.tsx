import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
} from 'recharts'
import type { ScaleScoreBreakdown } from '../api/respondent.mapper'

type Props = {
  scales: ScaleScoreBreakdown[]
}

export default function RadarBlock({ scales }: Props) {
  if (scales.length < 3) {
    return (
      <div className="result-empty">
        Радар отображается, когда методика содержит 3 шкалы и больше.
      </div>
    )
  }
  const data = scales.map((s) => ({
    scale: s.scaleName,
    value: s.value,
  }))
  return (
    <div className="result-chart-wrap" data-testid="radar-block">
      <ResponsiveContainer width="100%" aspect={1}>
        <RadarChart data={data} outerRadius="72%">
          <PolarGrid stroke="#CBD5E1" />
          <PolarAngleAxis
            dataKey="scale"
            tick={{ fontSize: 11, fill: '#475569' }}
          />
          <PolarRadiusAxis
            angle={90}
            domain={[0, 100]}
            tick={{ fontSize: 10, fill: '#94A3B8' }}
            tickCount={5}
          />
          <Radar
            name="Шкалы"
            dataKey="value"
            stroke="#5260FF"
            fill="#5260FF"
            fillOpacity={0.25}
            isAnimationActive
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  )
}
