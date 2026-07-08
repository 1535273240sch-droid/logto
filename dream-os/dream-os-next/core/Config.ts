/**
 * Config — 全局配置中心
 *
 * 存储可配置参数，支持环境变量覆盖。
 */

type ConfigKey = "api_base_url" | "default_model" | "temperature" | "max_tokens" | "max_loop_iterations";

class Config {
  private static _instance: Config;
  private _config: Record<string, string | number> = {};

  private constructor() {
    // 默认配置
    this._config = {
      api_base_url: "/api",
      default_model: "gpt-4o",
      temperature: "0.7",
      max_tokens: "1024",
      max_loop_iterations: "3",
    };
  }

  static getInstance(): Config {
    if (!Config._instance) {
      Config._instance = new Config();
    }
    return Config._instance;
  }

  getString(key: ConfigKey, defaultValue: string): string {
    return this._config[key] ?? defaultValue;
  }

  getNumber(key: ConfigKey, defaultValue: number): number {
    const v = this._config[key];
    return v !== undefined ? Number(v) : defaultValue;
  }

  set(key: ConfigKey, value: string | number): void {
    this._config[key] = value;
  }

  /** 从环境变量加载 */
  loadFromEnv(): void {
    const envs: Record<string, ConfigKey> = {
      NEXT_PUBLIC_API_BASE_URL: "api_base_url",
      NEXT_PUBLIC_DEFAULT_MODEL: "default_model",
      NEXT_PUBLIC_AI_TEMPERATURE: "temperature",
      NEXT_PUBLIC_AI_MAX_TOKENS: "max_tokens",
      NEXT_PUBLIC_MAX_LOOP_ITERATIONS: "max_loop_iterations",
    };
    for (const [envKey, configKey] of Object.entries(envs)) {
      if (typeof process !== "undefined" && process.env && process.env[envKey]) {
        this._config[configKey] = process.env[envKey]!;
      }
    }
  }
}

export const config = Config.getInstance();
export default config;
