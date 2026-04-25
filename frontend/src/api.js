const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')

const commonErrorLabels = {
  'Not Found': '未找到对应资源',
  'Internal Server Error': '服务内部错误',
  'Method Not Allowed': '请求方法不被允许',
  'API route not found': '接口地址不存在',
}

function buildUrl(path) {
  if (/^https?:\/\//.test(path)) return path
  return `${API_BASE_URL}${path}`
}

async function buildErrorMessage(response) {
  const text = await response.text()
  let detail = text
  try {
    const data = JSON.parse(text)
    detail = data.detail || data.message || text
  } catch {}

  const translated = commonErrorLabels[detail] || detail || '请求失败'
  return `请求失败（${response.status}）：${translated}`
}

export async function apiGet(path) {
  const response = await fetch(buildUrl(path))
  if (!response.ok) throw await buildErrorMessage(response)
  return await response.json()
}

export async function apiSend(path, method = 'POST', body = undefined) {
  const response = await fetch(buildUrl(path), {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!response.ok) throw await buildErrorMessage(response)
  return await response.json()
}