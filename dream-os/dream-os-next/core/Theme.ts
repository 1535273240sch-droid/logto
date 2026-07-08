/**
 * Theme — Dream Design Language (DDL) 设计语言
 *
 * 全局统一主题 Token。
 * 所有组件引用 Theme，禁止硬编码颜色/圆角/间距。
 */

import { ThemeTokens } from "../types/dream";

export const theme: ThemeTokens = {
  colors: {
    bgPrimary:       "#000000",
    bgSecondary:     "#050508",
    bgCard:          "rgba(255,255,255,0.03)",
    bgGlass:         "rgba(255,255,255,0.04)",
    border:          "rgba(255,255,255,0.08)",
    borderGlass:     "rgba(255,255,255,0.1)",
    textPrimary:     "#ffffff",
    textSecondary:   "#c8c8d4",
    textMuted:       "#9494a4",
    accent:          "#6c5ce7",
    accentHover:     "#7c6cf7",
    accentLight:     "#a29bfe",
    success:         "#00b894",
    error:           "#e17055",
    warning:         "#fdcb6e",
  },

  radii: {
    button:   16,
    input:    20,
    card:     20,
    cardLarge: 24,
    modal:    28,
  },

  spacing: {
    xs:   8,
    sm:   16,
    md:   24,
    lg:   32,
    xl:   40,
    xxl:  48,
    xxxl: 64,
  },

  fontSize: {
    logo:    44,
    h1:      28,
    h2:      22,
    body:    16,
    caption: 14,
    status:  13,
  },

  fontWeight: {
    regular: 400,
    medium:  500,
  },
};

/** 将 spacing 转为 CSS px 字符串 */
export function sp(value: number): string {
  return `${value}px`;
}

/** 获取主题色 */
export function color(key: keyof ThemeTokens["colors"]): string {
  return theme.colors[key];
}

/** 获取圆角 */
export function radius(key: keyof ThemeTokens["radii"]): string {
  return `${theme.radii[key]}px`;
}

export default theme;
