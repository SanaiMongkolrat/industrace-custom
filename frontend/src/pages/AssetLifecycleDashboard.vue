<!--
  AssetLifecycleDashboard.vue
  Page: /utility/asset-lifecycle
  Backend: GET /api/dashboard/asset-lifecycle
  Store:  src/store/assetLifecycleDashboard.js

  Widgets:
    1. KPI strip (4 tiles)
    2. Years remaining distribution (bar + donut)
    3. Assets needing attention (sortable, filterable table)
    4. Site x lifecycle heatmap (chartjs-chart-matrix or grouped bar fallback)
    5. Status badges (inline in table)
-->
<template>
  <div class="asset-lifecycle-dashboard">
    <div class="dashboard-header">
      <div class="header-text">
        <h1>Asset Lifecycle Dashboard</h1>
        <p class="subtitle">Years remaining and EoS status for {{ summary.total }} components</p>
        <p v-if="lastFetchedDisplay" class="last-fetched">Last updated: {{ lastFetchedDisplay }}</p>
      </div>
      <div class="header-actions">
        <Button
          icon="pi pi-refresh"
          :loading="loading"
          :label="loading ? 'Refreshing...' : 'Refresh'"
          class="p-button-outlined"
          @click="onRefreshClick"
        />
      </div>
    </div>

    <!-- Filter bar: cascading multi-select dropdowns for Site / Area / Asset Type / Manufacturer -->
    <div class="filter-bar" data-testid="filter-bar">
      <MultiSelect
        v-model="filters.sites"
        :options="filterOptions.sites"
        placeholder="All sites"
        display="chip"
        filter
        :max-selected-labels="3"
        class="filter-multi"
      />
      <MultiSelect
        v-model="filters.areas"
        :options="filterOptions.areas"
        placeholder="All areas"
        display="chip"
        filter
        :max-selected-labels="3"
        class="filter-multi"
      />
      <MultiSelect
        v-model="filters.assetTypes"
        :options="filterOptions.assetTypes"
        placeholder="All asset types"
        display="chip"
        filter
        :max-selected-labels="3"
        class="filter-multi"
      />
      <MultiSelect
        v-model="filters.manufacturers"
        :options="filterOptions.manufacturers"
        placeholder="All manufacturers"
        display="chip"
        filter
        :max-selected-labels="3"
        class="filter-multi"
      />
      <MultiSelect
        v-model="filters.locations"
        :options="filterOptions.locations"
        placeholder="All locations"
        display="chip"
        filter
        :max-selected-labels="3"
        class="filter-multi"
      />
      <Button
        v-if="filters.sites.length || filters.areas.length || filters.assetTypes.length || filters.manufacturers.length || filters.locations.length"
        label="Clear filters"
        icon="pi pi-times"
        class="p-button-text p-button-sm clear-filters-btn"
        @click="clearFilters"
      />
      <span class="filter-count">
        Showing <strong>{{ filteredComponents.length }}</strong> of {{ components.length }} components
      </span>
    </div>

    <!-- V10 — Data gap banner: visible when not_set > 80% -->
    <Message
      v-if="summary.total > 0 && summary.not_set / summary.total > 0.8"
      severity="info"
      :closable="true"
      class="gap-banner"
    >
      Only {{ summary.with_data }} of {{ summary.total }} components have lifecycle data configured.
      To improve coverage, set <code>useful_life_years</code> on asset types or model lifecycles.
    </Message>

    <!-- Pagination warning (V6 implicit) -->
    <Message
      v-if="paginationWarning"
      severity="warn"
      :closable="false"
      class="pagination-banner"
    >
      Fleet has exceeded the client-side threshold of 2,000 components.
      Performance may degrade. Server-side pagination is recommended.
    </Message>

    <!-- V6 — Loading / error states -->
    <div v-if="loading" class="loading">Loading dashboard...</div>
    <Message v-else-if="error" severity="error">{{ error }}</Message>

    <template v-else>
      <!-- W1: KPI strip -->
      <div class="kpi-strip">
        <div class="kpi-card" @click="setFilter('usefulLifeSource', null)">
          <div class="kpi-value">{{ summary.total }}</div>
          <div class="kpi-label">Total Components</div>
        </div>
        <div class="kpi-card kpi-good" @click="setFilter('usefulLifeSource', 'not_set')">
          <div class="kpi-value">{{ summary.not_set }}</div>
          <div class="kpi-label">Needs Configuration</div>
        </div>
        <div class="kpi-card kpi-info" @click="setFilter('usefulLifeSource', null)">
          <div class="kpi-value">{{ summary.with_data }}</div>
          <div class="kpi-label">With Data</div>
        </div>
        <div class="kpi-card kpi-warn" @click="setFilter('lifecycleStatus', 'END-OF-LIFE')">
          <div class="kpi-value">{{ summary.end_of_life + summary.near_eol }}</div>
          <div class="kpi-label">Near EoL / EoL</div>
        </div>
      </div>

      <!-- Active filter chips -->
      <div v-if="activeFilterCount > 0" class="active-filters">
        <Chip
          v-if="filters.lifecycleStatus"
          :label="`Status: ${filters.lifecycleStatus}`"
          removable
          @remove="setFilter('lifecycleStatus', null)"
        />
        <Chip
          v-if="filters.usefulLifeSource"
          :label="`Source: ${filters.usefulLifeSource}`"
          removable
          @remove="setFilter('usefulLifeSource', null)"
        />
        <Chip
          v-if="filters.siteName"
          :label="`Site: ${filters.siteName}`"
          removable
          @remove="setFilter('siteName', null)"
        />
        <Button label="Clear all" class="p-button-text p-button-sm" @click="clearFilters" />
      </div>

      <!-- W2: Years remaining distribution -->
      <Card class="widget">
        <template #title>Years Remaining Distribution</template>
        <template #content>
          <div v-if="distributionData.labels.length > 0" class="chart-container">
            <Doughnut
              v-if="hasAnyData"
              :data="distributionData"
              :options="donutOptions"
            />
            <Bar v-else :data="distributionData" :options="barOptions" />
          </div>
          <p v-else class="empty-state">No data to display</p>
        </template>
      </Card>

      <!-- W4: Site x lifecycle (rendered as grouped bar — matrix plugin not installable in this env) -->
      <Card class="widget">
        <template #title>Site x Lifecycle Status</template>
        <template #content>
          <div v-if="heatmapBarData.labels.length > 0" class="chart-container">
            <Bar :data="heatmapBarData" :options="heatmapBarOptions" />
          </div>
          <p v-else class="empty-state">No site data to display</p>
        </template>
      </Card>

      <!-- W3: Assets needing attention (table) + W5: Status badges -->
      <Card class="widget">
        <template #title>Assets Needing Attention</template>
        <template #content>
          <DataTable
            :value="filteredComponents"
            :paginator="true"
            :rows="20"
            :loading="loading"
            sortMode="multiple"
            responsiveLayout="scroll"
            class="lifecycle-table"
          >
            <Column field="asset_tag" header="Asset Tag" sortable />
            <Column field="asset_name" header="Asset Name" sortable />
            <Column field="manufacturer" header="Manufacturer" sortable />
            <Column field="model_name" header="Model" sortable />
            <Column field="lifespan_years" header="Lifespan (yrs)" sortable>
              <template #body="slotProps">
                {{ slotProps.data.lifespan_years !== null ? slotProps.data.lifespan_years.toFixed(2) : '—' }}
              </template>
            </Column>
            <Column field="effective_useful_life" header="Useful Life" sortable>
              <template #body="slotProps">
                {{ slotProps.data.effective_useful_life !== null ? slotProps.data.effective_useful_life : '—' }}
                <small v-if="slotProps.data.useful_life_source" class="source-label">
                  ({{ usefulLifeSourceLabel(slotProps.data.useful_life_source) }})
                </small>
              </template>
            </Column>
            <Column field="years_remaining" header="Years Remaining" sortable>
              <template #body="slotProps">
                <span v-if="slotProps.data.years_remaining === null" class="muted">—</span>
                <span
                  v-else-if="slotProps.data.years_remaining < 0"
                  class="years-red"
                >{{ slotProps.data.years_remaining.toFixed(2) }}</span>
                <span
                  v-else-if="slotProps.data.years_remaining <= 1"
                  class="years-amber"
                >{{ slotProps.data.years_remaining.toFixed(2) }}</span>
                <span v-else class="years-green">
                  {{ slotProps.data.years_remaining.toFixed(2) }}
                </span>
              </template>
            </Column>
            <Column field="model_eol_status" header="EoS" sortable>
              <template #body="slotProps">
                <Tag
                  v-if="slotProps.data.model_eol_status && slotProps.data.model_eol_status !== 'in_support'"
                  :value="eolLabel(slotProps.data.model_eol_status)"
                  :severity="eolSeverity(slotProps.data.model_eol_status)"
                />
                <span v-else class="muted">In support</span>
              </template>
            </Column>
            <Column field="plant_name" header="Site" sortable />
            <Column field="area_name" header="Area" sortable />
            <Column field="location_name" header="Location" sortable>
              <template #body="slotProps">
                <span v-if="slotProps.data.location_name">{{ slotProps.data.location_name }}</span>
                <span v-else class="muted">—</span>
              </template>
            </Column>
          </DataTable>
        </template>
      </Card>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, computed } from 'vue'
import { useAssetLifecycleDashboardStore } from '../store/assetLifecycleDashboard'
import { storeToRefs } from 'pinia'

// PrimeVue
import Card from 'primevue/card'
import Button from 'primevue/button'
import Chip from 'primevue/chip'
import Message from 'primevue/message'
import Tag from 'primevue/tag'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import MultiSelect from 'primevue/multiselect'

// Chart.js + vue-chartjs (already in deps). Registering all elements + scales
// used by Doughnut (ArcElement) and Bar (CategoryScale, LinearScale, BarElement).
// Tree-shaking safety: explicit side-effect import to keep register() calls.
import { Chart as ChartJS, ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement, Title } from 'chart.js'
import { Doughnut, Bar } from 'vue-chartjs'

ChartJS.register(ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement, Title)
// Note: chartjs-chart-matrix@3.x had a Vite/Rollup ESM resolution issue in this
// build env. Heatmap widget renders as a grouped/stacked bar chart instead —
// the data shape is the same and visually clearer at our 35-cell scale.
// Doughnut is the primary distribution chart; Bar is the fallback when there's
// no data (avoid rendering a doughnut of all zeros).
const hasAnyData = computed(() => {
  return distributionData.value.datasets[0]?.data?.some((v) => v > 0) || false
})

// Store
const store = useAssetLifecycleDashboardStore()
const { components, loading, error, lastFetched, filters, kpiSummary, filteredComponents, paginationWarning, activeFilterCount, filterOptions } =
  storeToRefs(store)
const summary = computed(() => kpiSummary.value)
const fetchDashboard = store.fetchDashboard
const setFilter = store.setFilter
const clearFilters = store.clearFilters

// Human-friendly "last updated" formatter (HH:MM:SS local time)
const lastFetchedDisplay = computed(() => {
  if (!lastFetched.value) return ''
  const d = new Date(lastFetched.value)
  return d.toLocaleTimeString()
})

// Refresh: manual button click
async function onRefreshClick() {
  await fetchDashboard()
}

// Refresh: browser tab focus / visibility return
function onVisibilityChange() {
  if (document.visibilityState === 'visible' && !loading.value) {
    fetchDashboard()
  }
}

// Computed: distribution data for W2 (bar/donut)
const distributionData = computed(() => {
  const buckets = {
    'Past useful life': 0,
    '≤ 1 year': 0,
    '1-3 years': 0,
    '3-5 years': 0,
    '> 5 years': 0,
  }
  for (const c of components.value) {
    if (c.years_remaining === null) continue
    if (c.years_remaining < 0) buckets['Past useful life']++
    else if (c.years_remaining <= 1) buckets['≤ 1 year']++
    else if (c.years_remaining <= 3) buckets['1-3 years']++
    else if (c.years_remaining <= 5) buckets['3-5 years']++
    else buckets['> 5 years']++
  }
  return {
    labels: Object.keys(buckets),
    datasets: [
      {
        label: 'Components',
        data: Object.values(buckets),
        backgroundColor: ['#ef4444', '#f59e0b', '#eab308', '#22c55e', '#3b82f6'],
      },
    ],
  }
})

const donutOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { position: 'right' },
  },
  onClick: (event, elements) => {
    if (elements.length > 0) {
      const index = elements[0].index
      const label = distributionData.value.labels[index]
      const sourceMap = {
        'Past useful life': 'not_set',
        '≤ 1 year': 'not_set',
        '1-3 years': 'not_set',
        '3-5 years': 'not_set',
        '> 5 years': 'not_set',
      }
      setFilter('usefulLifeSource', sourceMap[label] || null)
    }
  },
}

const barOptions = {
  responsive: true,
  maintainAspectRatio: false,
  indexAxis: 'y',
  plugins: { legend: { display: false } },
  onClick: (event, elements) => {
    if (elements.length > 0) {
      const index = elements[0].index
      const label = distributionData.value.labels[index]
      setFilter('usefulLifeSource', 'not_set')
    }
  },
}

// Computed: Site x Lifecycle as a grouped/stacked bar chart (matrix plugin not available).
// Each site is a label on the X axis; one dataset per lifecycle status.
const heatmapBarData = computed(() => {
  const sitesSet = new Set()
  const statusCounts = new Map() // key: `${site}::${status}` -> count
  for (const c of components.value) {
    if (!c.plant_name) continue
    sitesSet.add(c.plant_name)
    const key = `${c.plant_name}::${c.lifecycle_status}`
    statusCounts.set(key, (statusCounts.get(key) || 0) + 1)
  }
  const sites = Array.from(sitesSet)
  const statusOrder = ['NORMAL', 'END-OF-LIFE']
  const colors = { 'NORMAL': '#22c55e', 'END-OF-LIFE': '#ef4444' }
  const datasets = statusOrder
    .filter(s => sites.some(site => statusCounts.has(`${site}::${s}`)))
    .map(s => ({
      label: s,
      data: sites.map(site => statusCounts.get(`${site}::${s}`) || 0),
      backgroundColor: colors[s] || '#94a3b8',
    }))
  return { labels: sites, datasets }
})

const heatmapBarOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { position: 'top' } },
  scales: {
    x: { stacked: false, title: { display: true, text: 'Site' } },
    y: { stacked: false, beginAtZero: true, title: { display: true, text: 'Components' } },
  },
  onClick: (event, elements) => {
    if (elements.length > 0) {
      const datasetIndex = elements[0].datasetIndex
      const index = elements[0].index
      const status = heatmapBarData.value.datasets[datasetIndex].label
      const site = heatmapBarData.value.labels[index]
      setFilter('lifecycleStatus', status === 'NORMAL' ? null : status)
      setFilter('siteName', site)
    }
  },
}

// Helpers
function usefulLifeSourceLabel(s) {
  return { model: 'from model', inherited_from_asset_type: 'from type', not_set: 'not set' }[s] || s
}

function eolLabel(s) {
  return {
    phase_out: 'Phase out',
    limited_support: 'Limited',
    no_spare_parts: 'No spares',
    obsolete: 'Obsolete',
    not_applicable: 'N/A',
  }[s] || s
}

function eolSeverity(s) {
  return { phase_out: 'warning', limited_support: 'warning', no_spare_parts: 'danger', obsolete: 'danger' }[s] || 'info'
}

onMounted(async () => {
  await fetchDashboard()
  // Auto-refresh when user returns to the tab (covers the "added components
  // in another tab" use case without constant polling).
  document.addEventListener('visibilitychange', onVisibilityChange)
})

// Cleanup listener when component unmounts (e.g., user navigates away)
onBeforeUnmount(() => {
  document.removeEventListener('visibilitychange', onVisibilityChange)
})
</script>

<style scoped>
.asset-lifecycle-dashboard {
  padding: 1.5rem;
}
.dashboard-header {
  margin-bottom: 1.5rem;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
}
.header-text { flex: 1; }
.header-actions { padding-top: 0.25rem; }
.dashboard-header h1 {
  margin: 0 0 0.25rem 0;
  font-size: 1.75rem;
}
.subtitle {
  color: #6b7280;
  margin: 0;
}
.last-fetched {
  color: #9ca3af;
  font-size: 0.75rem;
  margin: 0.25rem 0 0 0;
  font-style: italic;
}
.gap-banner,
.pagination-banner {
  margin-bottom: 1rem;
}
.filter-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1rem;
  padding: 0.75rem 1rem;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
}
.filter-bar .filter-multi {
  min-width: 200px;
  max-width: 320px;
  flex: 1 1 200px;
}
.filter-bar .filter-count {
  margin-left: auto;
  font-size: 0.875rem;
  color: #6b7280;
}
.filter-bar .clear-filters-btn {
  margin-left: 0.5rem;
}
.kpi-strip {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
  margin-bottom: 1.5rem;
}
.kpi-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  padding: 1.25rem;
  cursor: pointer;
  transition: transform 0.15s;
}
.kpi-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}
.kpi-value {
  font-size: 2rem;
  font-weight: 700;
  color: #111827;
}
.kpi-label {
  font-size: 0.875rem;
  color: #6b7280;
  margin-top: 0.25rem;
}
.kpi-good .kpi-value { color: #16a34a; }
.kpi-warn .kpi-value { color: #f59e0b; }
.kpi-info .kpi-value { color: #3b82f6; }
.widget {
  margin-bottom: 1.5rem;
}
.chart-container {
  height: 300px;
  position: relative;
}
.empty-state {
  color: #9ca3af;
  text-align: center;
  padding: 2rem;
}
.active-filters {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  margin-bottom: 1rem;
  flex-wrap: wrap;
}
.years-red { color: #ef4444; font-weight: 600; }
.years-amber { color: #f59e0b; font-weight: 600; }
.years-green { color: #16a34a; font-weight: 600; }
.muted { color: #9ca3af; }
.source-label { color: #6b7280; font-size: 0.75rem; margin-left: 0.25rem; }
.loading {
  text-align: center;
  padding: 3rem;
  color: #6b7280;
}
</style>
