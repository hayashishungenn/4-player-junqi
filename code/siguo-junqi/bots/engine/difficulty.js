// 多档难度配置（P2）
//
// 主引擎没有 ELO / Skill 限制，棋力由「思考时间预算」间接控制：预算越大，
// 采样批次越多、搜索深度越高（见 search.js chooseStrongMove 第 314 行）。
// 本模块只提供档位到引擎选项的映射，不修改任何现有引擎行为、不新增依赖、
// 不改动公共 API。档位名称与数值均为工程约定，不代表 ELO 或胜率。

export const DIFFICULTY_LEVELS = Object.freeze([
  Object.freeze({ id: 1, name: '入门', budgetMs: 150, maxSamples: 4, maxDepth: 2,
    description: '极短思考，仅少量采样与浅层搜索，适合熟悉规则。' }),
  Object.freeze({ id: 2, name: '初级', budgetMs: 400, maxSamples: 12, maxDepth: 3,
    description: '短思考，能处理简单交战与夺旗。' }),
  Object.freeze({ id: 3, name: '中级', budgetMs: 1000, maxSamples: 32, maxDepth: 4,
    description: '常规思考，具备军旗防护与工兵战术。' }),
  Object.freeze({ id: 4, name: '高级', budgetMs: 2200, maxSamples: 64, maxDepth: 5,
    description: '较长思考，对家协作与暗棋推断更充分。' }),
  Object.freeze({ id: 5, name: '大师', budgetMs: 4000, maxSamples: 128, maxDepth: 5,
    description: '最大思考预算，接近引擎本地棋力上限。' }),
]);

const byId = new Map(DIFFICULTY_LEVELS.map(level => [level.id, level]));
const byName = new Map(DIFFICULTY_LEVELS.map(level => [level.name, level]));

/** 按 id 或名称解析档位；未知值返回 null，不静默回退到某个档位。 */
export function resolveDifficulty(value) {
  if (value == null) return null;
  if (typeof value === 'number') return byId.get(value) || null;
  const key = String(value).trim();
  return byName.get(key) || byId.get(Number(key)) || null;
}

/** 生成引擎选项；overrides 可覆盖预算/采样/深度，但预算至少 1ms、采样至少 1、深度至少 1。 */
export function engineOptions(level, overrides = {}) {
  const resolved = resolveDifficulty(level);
  if (!resolved) throw new Error(`未知难度档位：${level}`);
  const budgetMs = overrides.budgetMs ?? resolved.budgetMs;
  const maxSamples = overrides.maxSamples ?? resolved.maxSamples;
  const maxDepth = overrides.maxDepth ?? resolved.maxDepth;
  if (!Number.isFinite(budgetMs) || budgetMs < 1) throw new Error('budgetMs 必须为正数');
  if (!Number.isInteger(maxSamples) || maxSamples < 1) throw new Error('maxSamples 必须为正整数');
  if (!Number.isInteger(maxDepth) || maxDepth < 1) throw new Error('maxDepth 必须为正整数');
  return { level: resolved.id, name: resolved.name, budgetMs, maxSamples, maxDepth };
}
