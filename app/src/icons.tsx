// Icon map — port 1:1 dari map `Ic` di ui/src/App.jsx, pakai react-native-svg.
// Warna = prop `color` (pengganti currentColor), ukuran = prop `size` (default dari width web).
// Stroke icons WAJIB stroke={color} — react-native-svg tidak kenal currentColor dari CSS.
import type { ReactElement } from 'react'
import Svg, { Circle, Path } from 'react-native-svg'

export interface IconProps {
  color: string
  size?: number
}
export type Icon = (p: IconProps) => ReactElement

const S = (c: string) => ({
  fill: 'none' as const,
  stroke: c,
  strokeWidth: 2,
  strokeLinecap: 'round' as const,
})

export const Ic: Record<string, Icon> = {
  search: ({ color, size = 18 }) => (
    <Svg width={size} height={size} viewBox="0 0 24 24" {...S(color)}>
      <Circle cx={11} cy={11} r={7} />
      <Path d="m21 21-4.3-4.3" />
    </Svg>
  ),
  play: ({ color, size = 16 }) => (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill={color}>
      <Path d="M8 5.14v13.72a1 1 0 0 0 1.5.86l11-6.86a1 1 0 0 0 0-1.72l-11-6.86a1 1 0 0 0-1.5.86Z" />
    </Svg>
  ),
  playLg: ({ color, size = 20 }) => (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill={color}>
      <Path d="M8 5.14v13.72a1 1 0 0 0 1.5.86l11-6.86a1 1 0 0 0 0-1.72l-11-6.86a1 1 0 0 0-1.5.86Z" />
    </Svg>
  ),
  down: ({ color, size = 16 }) => (
    <Svg width={size} height={size} viewBox="0 0 24 24" {...S(color)} strokeLinejoin="round">
      <Path d="M12 3v12" />
      <Path d="m7 11 5 5 5-5" />
      <Path d="M4 21h16" />
    </Svg>
  ),
  back: ({ color, size = 18 }) => (
    <Svg width={size} height={size} viewBox="0 0 24 24" {...S(color)} strokeLinejoin="round">
      <Path d="M19 12H5" />
      <Path d="m12 19-7-7 7-7" />
    </Svg>
  ),
  forward: ({ color, size = 18 }) => (
    <Svg width={size} height={size} viewBox="0 0 24 24" {...S(color)} strokeLinejoin="round">
      <Path d="M5 12h14" />
      <Path d="m12 5 7 7-7 7" />
    </Svg>
  ),
  home: ({ color, size = 18 }) => (
    <Svg width={size} height={size} viewBox="0 0 24 24" {...S(color)} strokeLinejoin="round">
      <Path d="m3 10 9-7 9 7v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z" />
    </Svg>
  ),
  x: ({ color, size = 16 }) => (
    <Svg width={size} height={size} viewBox="0 0 24 24" {...S(color)}>
      <Path d="M18 6 6 18M6 6l12 12" />
    </Svg>
  ),
  // Web pakai satu `chev` (object literal: entri kanan menimpa entri bawah).
  // RankCard pakai "›" (18). ResSelect pakai yang sama, di-rotate 180deg saat open.
  chev: ({ color, size = 18 }) => (
    <Svg width={size} height={size} viewBox="0 0 24 24" {...S(color)} strokeLinejoin="round">
      <Path d="m9 18 6-6-6-6" />
    </Svg>
  ),
  flame: ({ color, size = 18 }) => (
    <Svg width={size} height={size} viewBox="0 0 24 24" {...S(color)} strokeLinejoin="round">
      <Path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z" />
    </Svg>
  ),
  clock: ({ color, size = 18 }) => (
    <Svg width={size} height={size} viewBox="0 0 24 24" {...S(color)} strokeLinejoin="round">
      <Circle cx={12} cy={12} r={10} />
      <Path d="M12 6v6l4 2" />
    </Svg>
  ),
  star: ({ color, size = 16 }) => (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill={color}>
      <Path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
    </Svg>
  ),
}