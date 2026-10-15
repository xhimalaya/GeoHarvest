import { createRouter, createWebHistory } from 'vue-router'
import HarvestView from '../views/HarvestView.vue'
import JobsView from '../views/JobsView.vue'
import CatalogView from '../views/CatalogView.vue'
import ProcessingView from '../views/ProcessingView.vue'
import SettingsView from '../views/SettingsView.vue'
import FileManagerView from '../views/FileManagerView.vue'
import TopoSheetsView from '../views/TopoSheetsView.vue'
import EarthEngineView from '../views/EarthEngineView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'harvest',
      component: HarvestView,
    },
    {
      path: '/earthengine',
      name: 'earthengine',
      component: EarthEngineView,
    },
    {
      path: '/toposheets',
      name: 'toposheets',
      component: TopoSheetsView,
    },
    {
      path: '/jobs',
      name: 'jobs',
      component: JobsView,
    },
    {
      path: '/catalog',
      name: 'catalog',
      component: CatalogView,
    },
    {
      path: '/processing',
      name: 'processing',
      component: ProcessingView,
    },
    {
      path: '/files',
      name: 'files',
      component: FileManagerView,
    },
    {
      path: '/settings',
      name: 'settings',
      component: SettingsView,
    },
  ],
})

export default router
