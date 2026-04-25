import { createRouter, createWebHistory } from 'vue-router'
import DashboardView from './views/DashboardView.vue'
import StudyView from './views/StudyView.vue'
import KnowledgeBaseView from './views/KnowledgeBaseView.vue'
import MaterialsView from './views/MaterialsView.vue'
import PublishView from './views/PublishView.vue'
import LogsView from './views/LogsView.vue'
import SettingsView from './views/SettingsView.vue'

const routes = [
  { path: '/', component: DashboardView },
  { path: '/study', component: StudyView },
  { path: '/knowledge-base', component: KnowledgeBaseView },
  { path: '/materials', component: MaterialsView },
  { path: '/publish', component: PublishView },
  { path: '/logs', component: LogsView },
  { path: '/settings', component: SettingsView },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
