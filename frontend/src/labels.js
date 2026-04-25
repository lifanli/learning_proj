const taskKindLabels = {
  'curriculum.generate': '课程表生成',
  'curriculum.auto_study': '自动学习',
  'study.manual': '手动学习',
  'publish.book': '出版任务',
}

const taskStatusLabels = {
  pending: '待处理',
  queued: '排队中',
  running: '运行中',
  succeeded: '成功',
  failed: '失败',
  canceled: '已取消',
  cancel_requested: '正在取消',
  interrupted: '已中断',
}

const curriculumStatusLabels = {
  none: '暂无',
  draft: '草稿',
  approved: '已批准',
  in_progress: '进行中',
  completed: '已完成',
  done: '已完成',
  pending: '待处理',
  failed: '失败',
}

const depthLabels = {
  quick: '快速',
  comprehensive: '全面',
  expert: '专家',
}

const manualModeLabels = {
  'study-topic': '按主题学习',
  'study-course': '按课程学习',
  'study-github': '学习代码仓库',
  'study-arxiv': '学习论文',
  'study-wechat': '学习公众号文章',
}

const sourceTypeLabels = {
  arxiv: '论文',
  github: '代码仓库',
  web: '网页',
  wechat: '公众号',
  course: '课程',
  topic: '主题',
}

const taskMessageLabels = {
  'Task queued': '任务已加入队列。',
  'No details yet.': '暂无详情。',
  'Cancellation requested. Running Python work will stop when it reaches a safe boundary.':
    '已请求取消。正在运行的任务会在安全边界处停止。',
  'Task was interrupted before API restart': '任务在接口服务重启前被中断。',
  'The API process stopped before this task reached a terminal state.': '接口服务在任务结束前停止。',
}

function formatWithMap(value, labels, fallback = '暂无') {
  if (value === undefined || value === null || value === '') return fallback
  const text = String(value)
  return labels[text] || fallback
}

export function formatTaskKind(value) {
  return formatWithMap(value, taskKindLabels, '未知任务')
}

export function formatTaskStatus(value) {
  return formatWithMap(value, taskStatusLabels, '未知状态')
}

export function formatCurriculumStatus(value) {
  return formatWithMap(value, curriculumStatusLabels, '未知状态')
}

export function formatDepth(value) {
  return formatWithMap(value, depthLabels, '未知深度')
}

export function formatManualMode(value) {
  return formatWithMap(value, manualModeLabels, '未知模式')
}

export function formatSourceType(value) {
  return formatWithMap(value, sourceTypeLabels, '其他来源')
}

export function translateTaskText(value) {
  if (!value) return ''
  let text = String(value)

  if (taskMessageLabels[text]) return taskMessageLabels[text]

  for (const [kind, label] of Object.entries(taskKindLabels)) {
    const lifecycleLabels = {
      [`${kind} started`]: `${label}已开始。`,
      [`${kind} finished`]: `${label}已完成。`,
      [`${kind} failed`]: `${label}失败。`,
      [`${kind} canceled`]: `${label}已取消。`,
      [`${kind} canceled before start`]: `${label}在启动前已取消。`,
    }
    if (lifecycleLabels[text]) return lifecycleLabels[text]
  }

  text = text
    .replace(/\bstatus=/g, '状态=')
    .replace(/\btitle=/g, '标题=')
    .replace(/\boutput_dir=/g, '输出目录=')
    .replace(/\boutput_path=/g, '输出路径=')
    .replace(/\bcompleted=/g, '完成=')
    .replace(/\bfailed=/g, '失败=')
    .replace(/\bskipped=/g, '跳过=')
    .replace(/\btotal=/g, '总数=')
    .replace(/\bsucceeded\b/g, '成功')
    .replace(/\bfailed\b/g, '失败')
    .replace(/\bcanceled\b/g, '已取消')
    .replace(/\binterrupted\b/g, '已中断')

  return text
}