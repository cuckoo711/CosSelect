import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useSessionStore } from '@/stores/session'

const routes: RouteRecordRaw[] = [
  { path: '/', name: 'portal', component: () => import('@/views/Portal.vue') },
  { path: '/leader/create', name: 'leader-create', component: () => import('@/views/LeaderCreate.vue') },
  { path: '/join', name: 'join', component: () => import('@/views/JoinSpace.vue') },
  {
    path: '/space/:spaceId',
    name: 'space',
    component: () => import('@/views/SpaceHome.vue'),
    props: true,
  },
  {
    path: '/space/:spaceId/manage',
    name: 'manage',
    component: () => import('@/views/LeaderManage.vue'),
    props: true,
    meta: { leader: true },
  },
  {
    path: '/space/:spaceId/stats',
    name: 'stats',
    component: () => import('@/views/StatsDashboard.vue'),
    props: true,
    meta: { leader: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const session = useSessionStore()
  // guard space routes: must be authed for that space
  if (to.name === 'space' || to.meta.leader) {
    const sid = String(to.params.spaceId)
    if (!session.authed || session.spaceId !== sid) {
      return { name: 'portal' }
    }
    if (to.meta.leader && !session.isLeader) {
      return { name: 'space', params: { spaceId: sid } }
    }
  }
  return true
})

export default router
