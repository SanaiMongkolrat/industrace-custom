<!--
  - App.vue
  - Componente principale dell'applicazione
  - Utilizza Menubar per la navigazione
  - Utilizza Toast per la gestione degli avvisi
  - Utilizza Dropdown per la selezione della lingua
  - Utilizza router-view per la gestione delle route
  - Utilizza auth store per la gestione dell'autenticazione
-->
<template>
  <div class="app-container">
    <Toast />
    <SetupDetector />
    <div v-if="auth.isAuthenticated" class="layout">
      <SidebarMenu />
      <div class="main-content">
        <router-view />
      </div>
    </div>
    <div v-else>
      <router-view />
    </div>
    <GlobalSearchSpotlight />
    <BaseFooter v-if="auth.isAuthenticated" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from './store/auth'
import { useI18n } from 'vue-i18n'

import Menubar from 'primevue/menubar'
import Toast from 'primevue/toast'
import Dropdown from 'primevue/dropdown'
import SidebarMenu from './components/common/SidebarMenu.vue'
import GlobalSearchSpotlight from './components/common/GlobalSearchSpotlight.vue'
import BaseFooter from './components/common/BaseFooter.vue'
import SetupDetector from './components/SetupDetector.vue'

const { t, locale } = useI18n()
const router = useRouter()
const auth = useAuthStore()

const languages = [
  { label: 'Italiano', code: 'it' },
  { label: 'English', code: 'en' }
]

const currentLocale = ref('en')

const menuItems = [
  { labelKey: 'menu.dashboard', icon: 'pi pi-home', route: '/' },
  { labelKey: 'menu.assets', icon: 'pi pi-server', route: '/assets' },
  { labelKey: 'menu.sites', icon: 'pi pi-map-marker', route: '/sites' },
  { labelKey: 'menu.suppliers', icon: 'pi pi-map-marker', route: '/suppliers' },
  { labelKey: 'menu.manufacturers', icon: 'pi pi-id-card', route: '/manufacturers' },
  { labelKey: 'menu.utility', icon: 'pi pi-box', route: '/utility' },
  { labelKey: 'menu.users', icon: 'pi pi-users', route: '/users' },
  { labelKey: 'menu.assettypes', icon: 'pi pi-server', route: '/asset-types' },
  { labelKey: 'menu.logout', icon: 'pi pi-sign-out', action: () => { auth.logout(); router.push('/login') }, class: 'logout-item' }
]

// Computed per creare i menu tradotti con funzione t()
const translatedMenuItems = computed(() => {
  return menuItems.map(item => {
    return {
      label: t(item.labelKey),
      icon: item.icon,
      command: item.route ? () => router.push(item.route) : item.action,
      class: item.class || ''
    }
  })
})

// Cambia lingua e salva localStorage
function onChangeLanguage(e) {
  locale.value = e.value
  localStorage.setItem('user-lang', e.value)
}

onMounted(async () => {
  locale.value = currentLocale.value
  if (!auth.isAuthenticated) {
    await auth.fetchUser()
  }
  if (auth.isAuthenticated) {
    auth.startTokenRefresh()
  }
})
</script>

<style scoped>
.app-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
.layout {
  display: flex;
  flex: 1;
  min-height: 0;
}
.main-content {
  flex: 1;
  padding: 2rem;
  overflow-y: auto;
}

.logout-item {
  margin-left: auto;
}

.p-menubar {
  border-radius: 0;
  border-left: none;
  border-right: none;
  border-top: none;
  padding: 0.5rem 2rem;
}
</style>
