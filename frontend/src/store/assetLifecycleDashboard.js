// store/assetLifecycleDashboard.js
// Pinia store for the Asset Lifecycle Monitoring Dashboard.
//
// Maximum fleet size for client-side interactive (no pagination): 2,000 components.
// Beyond this, implement server-side pagination:
//   GET /api/dashboard/asset-lifecycle?page=N&limit=50
// Tracked: 2026-09-07 fleet-state shows 832 components. Threshold = 2,000.

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api/api'

const MAX_COMPONENTS_NO_PAGINATION = 2000

export const useAssetLifecycleDashboardStore = defineStore(
  'assetLifecycleDashboard',
  () => {
    const components = ref([])
    const loading = ref(false)
    const error = ref(null)
    const lastFetched = ref(null) // ISO timestamp of last successful fetch (returned below)
    const filters = ref({
      lifecycleStatus: null, // 'NORMAL' | 'END-OF-LIFE' | null
      usefulLifeSource: null, // 'model' | 'inherited_from_asset_type' | 'not_set' | null
      siteName: null, // string | null
    })

    const filteredComponents = computed(() => {
      return components.value.filter((c) => {
        if (filters.value.lifecycleStatus && c.lifecycle_status !== filters.value.lifecycleStatus) return false
        if (filters.value.usefulLifeSource && c.useful_life_source !== filters.value.usefulLifeSource) return false
        if (filters.value.siteName && c.plant_name !== filters.value.siteName) return false
        return true
      })
    })

    const kpiSummary = computed(() => {
      const total = components.value.length
      const withData = components.value.filter((c) => c.useful_life_source !== 'not_set').length
      const nearEol = components.value.filter(
        (c) => c.years_remaining !== null && c.years_remaining > 0 && c.years_remaining <= 1.0
      ).length
      const endOfLife = components.value.filter((c) => c.lifecycle_status === 'END-OF-LIFE').length
      return {
        total,
        with_data: withData,
        not_set: total - withData,
        near_eol: nearEol,
        end_of_life: endOfLife,
      }
    })

    const paginationWarning = computed(() => components.value.length > MAX_COMPONENTS_NO_PAGINATION)

    const activeFilterCount = computed(() => {
      return Object.values(filters.value).filter((v) => v !== null).length
    })

    async function fetchDashboard() {
      loading.value = true
      error.value = null
      try {
        const response = await api.getAssetLifecycleDashboard()
        // Axios wraps response — actual API body is in response.data
        components.value = response?.data?.components || []
        lastFetched.value = new Date().toISOString()
      } catch (err) {
        error.value = err.message || 'Failed to load dashboard data'
        components.value = []
        lastFetched.value = null
      } finally {
        loading.value = false
      }
    }

    function setFilter(key, value) {
      if (key in filters.value) {
        filters.value[key] = value
      }
    }

    function clearFilters() {
      filters.value = {
        lifecycleStatus: null,
        usefulLifeSource: null,
        siteName: null,
      }
    }

    return {
      // state
      components,
      loading,
      error,
      lastFetched,
      filters,
      // getters
      filteredComponents,
      kpiSummary,
      paginationWarning,
      activeFilterCount,
      // actions
      fetchDashboard,
      setFilter,
      clearFilters,
    }
  }
)
