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
    const lastFetched = ref(null) // ISO timestamp of last successful fetch
    const filters = ref({
      lifecycleStatus: null, // 'NORMAL' | 'END-OF-LIFE' | null
      usefulLifeSource: null, // 'model' | 'inherited_from_asset_type' | 'not_set' | null
      siteName: null, // string | null (legacy single-value, kept for KPI click-to-filter)
      sites: [], // string[] — multi-select from the filter bar
      areas: [], // string[] — multi-select from the filter bar
      assetTypes: [], // string[] — multi-select from the filter bar
      manufacturers: [], // string[] — multi-select from the filter bar
      locations: [], // string[] — multi-select from the filter bar (cabinet name)
    })

    const filteredComponents = computed(() => {
      return components.value.filter((c) => {
        if (filters.value.lifecycleStatus && c.lifecycle_status !== filters.value.lifecycleStatus) return false
        if (filters.value.usefulLifeSource && c.useful_life_source !== filters.value.usefulLifeSource) return false
        if (filters.value.siteName && c.site_code !== filters.value.siteName) return false
        // Multi-select filters (any-of semantics: empty array = no filter)
        if (filters.value.sites.length > 0 && !filters.value.sites.includes(c.site_code)) return false
        if (filters.value.areas.length > 0 && !filters.value.areas.includes(c.area_name)) return false
        if (filters.value.assetTypes.length > 0 && !filters.value.assetTypes.includes(c.asset_type_name)) return false
        if (filters.value.manufacturers.length > 0 && !filters.value.manufacturers.includes(c.manufacturer)) return false
        if (filters.value.locations.length > 0 && !filters.value.locations.includes(c.location_name)) return false
        return true
      })
    })

    // Distinct values for filter dropdowns (derived from the full dataset, not
    // the filtered one, so the dropdown options don't disappear as you filter).
    const filterOptions = computed(() => {
      const sites = new Set()
      const areas = new Set()
      const assetTypes = new Set()
      const manufacturers = new Set()
      const locations = new Set()
      for (const c of components.value) {
        if (c.site_code) sites.add(c.site_code)
        if (c.area_name) areas.add(c.area_name)
        if (c.asset_type_name) assetTypes.add(c.asset_type_name)
        if (c.manufacturer) manufacturers.add(c.manufacturer)
        if (c.location_name) locations.add(c.location_name)
      }
      return {
        sites: Array.from(sites).sort(),
        areas: Array.from(areas).sort(),
        assetTypes: Array.from(assetTypes).sort(),
        manufacturers: Array.from(manufacturers).sort(),
        locations: Array.from(locations).sort(),
      }
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
        sites: [],
        areas: [],
        assetTypes: [],
        manufacturers: [],
        locations: [],
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
      filterOptions,
      // actions
      fetchDashboard,
      setFilter,
      clearFilters,
    }
  }
)
