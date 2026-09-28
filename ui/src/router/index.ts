import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'gallery',
      component: () => import('../pages/Gallery.vue'),
    },
    {
      path: '/runs',
      name: 'runs',
      component: () => import('../pages/RunHistory.vue'),
    },
    {
      path: '/runs/:id',
      name: 'run-detail',
      component: () => import('../pages/RunDetail.vue'),
    },
    {
      path: '/builder',
      name: 'builder',
      component: () => import('../pages/Builder.vue'),
    },
    {
      path: '/new',
      name: 'run-form',
      component: () => import('../pages/RunForm.vue'),
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/',
    },
  ],
})

export default router
