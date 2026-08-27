<template>
  <div class="model-lifecycles-page">
    <div class="page-header">
      <h1>{{ t('modelLifecycles.title') }}</h1>
      <div class="header-actions">
        <Button 
          v-if="canWrite('model_lifecycles')" 
          :label="t('common.actions.create')" 
          icon="pi pi-plus" 
          @click="showCreateDialog = true" 
        />
        <Button 
          v-if="canWrite('model_lifecycles')"
          :label="t('common.actions.import')" 
          icon="pi pi-upload" 
          class="p-button-secondary"
          @click="triggerImport" 
        />
        <input type="file" ref="fileInput" accept=".csv" style="display:none" @change="onFileSelected" />
        <a :href="templateUrl" download class="p-button p-button-sm p-button-outlined">
          <i class="pi pi-download mr-2" />{{ t('common.actions.downloadTemplate') }}
        </a>
      </div>
    </div>

    <div class="stats-bar" v-if="stats">
      <div class="stat-card" v-for="(count, status) in stats" :key="status">
        <span class="stat-value">{{ count }}</span>
        <span class="stat-label">{{ t('modelLifecycles.status.' + status) }}</span>
      </div>
    </div>

    <DataTable 
      :value="filteredLifecycles" 
      :loading="loading" 
      paginator 
      :rows="15" 
      :rowsPerPageOptions="[10, 15, 25, 50]"
      sortField="manufacturer_name"
      :sortOrder="1"
    >
      <template #header>
        <div class="flex justify-content-between align-items-center gap-2">
          <div class="flex align-items-center gap-2">
            <span class="p-input-icon-left">
              <i class="pi pi-search" />
              <InputText 
                v-model="searchQuery" 
                :placeholder="t('common.actions.search')" 
                class="w-12rem"
              />
            </span>
          </div>
          <div class="flex gap-2">
            <span class="text-sm text-600">
              {{ t('assets.messages.filteredAssets', { filtered: filteredLifecycles.length, total: lifecycles.length }) }}
            </span>
          </div>
        </div>
      </template>
      <Column field="manufacturer_name" :header="t('common.fields.manufacturer')" sortable></Column>
      <Column field="model_name" :header="t('common.fields.model')" sortable></Column>
      <Column field="asset_type_name" :header="t('modelLifecycles.fields.assetType')" sortable></Column>
      <Column field="lifecycle_status" :header="t('modelLifecycles.fields.lifecycleStatus')" sortable>
        <template #body="{ data }">
          <Tag :value="getStatusLabel(data.lifecycle_status)" :severity="getStatusSeverity(data.lifecycle_status)" />
        </template>
      </Column>
      <Column field="useful_life_years" :header="t('modelLifecycles.fields.usefulLifeYears')" sortable>
        <template #body="{ data }">
          <span v-if="data.useful_life_years">{{ data.useful_life_years }} {{ t('common.messages.years') }}</span>
          <span v-else>-</span>
        </template>
      </Column>
      <Column field="end_of_support_date" :header="t('modelLifecycles.fields.eosDate')" sortable>
        <template #body="{ data }">
          <span :class="{ 'text-danger': isOverdue(data.end_of_support_date) }">{{ formatDate(data.end_of_support_date) }}</span>
        </template>
      </Column>
      <Column field="spare_part_availability" :header="t('modelLifecycles.fields.spareParts')" sortable>
        <template #body="{ data }">
          <Tag v-if="data.spare_part_availability" :value="t('modelLifecycles.spareParts.' + data.spare_part_availability)" :severity="getSpareSeverity(data.spare_part_availability)" />
          <span v-else>-</span>
        </template>
      </Column>
      <Column field="asset_count" :header="t('modelLifecycles.fields.assetCount')" sortable></Column>
      <Column field="replacement_model" :header="t('modelLifecycles.fields.replacement')"></Column>
      <Column :header="t('common.strings.actions')" v-if="canWrite('model_lifecycles') || canDelete('model_lifecycles')">
        <template #body="{ data }">
          <Button 
            v-if="canWrite('model_lifecycles')"
            icon="pi pi-pencil" 
            class="p-button-rounded p-button-text p-button-info" 
            @click="editLifecycle(data)" 
          />
          <Button 
            v-if="canDelete('model_lifecycles')"
            icon="pi pi-trash" 
            class="p-button-rounded p-button-text p-button-danger" 
            @click="deleteLifecycle(data.id)" 
          />
        </template>
      </Column>
    </DataTable>

    <Dialog 
      v-model:visible="showCreateDialog" 
      :header="t('common.actions.create')" 
      :modal="true" 
      :style="{ width: '50vw' }"
    >
      <ModelLifecycleForm 
        :manufacturers="manufacturers"
        @submit="createLifecycle" 
        @cancel="showCreateDialog = false" 
      />
    </Dialog>

    <Dialog 
      v-model:visible="showEditDialog" 
      :header="t('common.actions.edit')" 
      :modal="true" 
      :style="{ width: '50vw' }"
    >
      <ModelLifecycleForm 
        :manufacturers="manufacturers"
        :lifecycle="editingLifecycle" 
        @submit="updateLifecycle" 
        @cancel="onEditCancel" 
      />
    </Dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useI18n } from 'vue-i18n'
import { usePermissions } from '../composables/usePermissions'
import api from '../api/api'
import ModelLifecycleForm from '../components/forms/ModelLifecycleForm.vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Tag from 'primevue/tag'
import InputText from 'primevue/inputtext'

const toast = useToast()
const { t } = useI18n()
const { canWrite, canDelete } = usePermissions()

const lifecycles = ref([])
const manufacturers = ref([])
const loading = ref(false)
const showCreateDialog = ref(false)
const showEditDialog = ref(false)
const editingLifecycle = ref(null)
const stats = ref(null)
const fileInput = ref(null)
const templateUrl = '/template_import_model_lifecycle.csv'
const searchQuery = ref('')

const filteredLifecycles = computed(() => {
  const q = searchQuery.value.toLowerCase().trim()
  if (!q) return lifecycles.value
  return lifecycles.value.filter(lc => {
    return (lc.manufacturer_name && lc.manufacturer_name.toLowerCase().includes(q))
      || (lc.model_name && lc.model_name.toLowerCase().includes(q))
      || (lc.asset_type_name && lc.asset_type_name.toLowerCase().includes(q))
      || (lc.lifecycle_status && lc.lifecycle_status.toLowerCase().includes(q))
      || (lc.replacement_model && lc.replacement_model.toLowerCase().includes(q))
  })
})

onMounted(() => {
  fetchLifecycles()
  fetchManufacturers()
  fetchStats()
})

async function fetchLifecycles() {
  loading.value = true
  try {
    const response = await api.getModelLifecycles({ limit: 1000 })
    lifecycles.value = response.data
  } catch (error) {
    toast.add({ severity: 'error', summary: t('common.messages.error'), detail: t('modelLifecycles.messages.fetchError'), life: 3000 })
  } finally {
    loading.value = false
  }
}

async function fetchManufacturers() {
  try {
    const response = await api.getManufacturers()
    manufacturers.value = response.data
  } catch (error) {
    // Silently fail - manufacturers are optional for the form
  }
}

async function fetchStats() {
  try {
    const response = await api.getModelLifecycleStats()
    stats.value = response.data
  } catch (error) {
    // Stats are optional
  }
}

function editLifecycle(lc) {
  editingLifecycle.value = { ...lc }
  nextTick(() => showEditDialog.value = true)
}

function onEditCancel() {
  showEditDialog.value = false
  editingLifecycle.value = null
}

async function createLifecycle(data) {
  try {
    await api.createModelLifecycle(data)
    toast.add({ severity: 'success', summary: t('common.messages.success'), detail: t('modelLifecycles.messages.created'), life: 3000 })
    showCreateDialog.value = false
    fetchLifecycles()
    fetchStats()
  } catch (err) {
    toast.add({ severity: 'error', summary: t('common.messages.error'), detail: t('modelLifecycles.messages.createError'), life: 3000 })
  }
}

async function updateLifecycle(data) {
  try {
    await api.updateModelLifecycle(editingLifecycle.value.id, data)
    toast.add({ severity: 'success', summary: t('common.messages.updated'), detail: t('modelLifecycles.messages.updated'), life: 3000 })
    showEditDialog.value = false
    fetchLifecycles()
    fetchStats()
  } catch (err) {
    toast.add({ severity: 'error', summary: t('common.messages.updateError'), detail: t('modelLifecycles.messages.updateError'), life: 3000 })
  }
}

async function deleteLifecycle(id) {
  if (!confirm(t('modelLifecycles.deleteConfirm'))) return
  try {
    await api.deleteModelLifecycle(id)
    toast.add({ severity: 'success', summary: t('common.messages.deleted'), detail: t('modelLifecycles.messages.deleted'), life: 3000 })
    fetchLifecycles()
    fetchStats()
  } catch (err) {
    toast.add({ severity: 'error', summary: t('common.messages.deleteError'), detail: t('modelLifecycles.messages.deleteError'), life: 3000 })
  }
}

function getStatusSeverity(status) {
  const map = {
    'in_support': 'success',
    'phase_out': 'warn',
    'limited_support': 'warn',
    'no_spare_parts': 'danger',
    'obsolete': 'danger',
    'not_applicable': 'info',
    'total': 'info'
  }
  return map[status] || 'info'
}

function getStatusLabel(status) {
  const map = {
    'in_support': t('modelLifecycles.status.in_support'),
    'phase_out': t('modelLifecycles.status.phase_out'),
    'limited_support': t('modelLifecycles.status.limited_support'),
    'no_spare_parts': t('modelLifecycles.status.no_spare_parts'),
    'obsolete': t('modelLifecycles.status.obsolete'),
    'not_applicable': t('modelLifecycles.status.not_applicable'),
    'total': t('modelLifecycles.status.total'),
  }
  return map[status] || status
}

function getSpareSeverity(avail) {
  const map = { 'available': 'success', 'limited': 'warn', 'unavailable': 'danger' }
  return map[avail] || 'info'
}

function isOverdue(date) {
  if (!date) return false
  return new Date(date) < new Date()
}

function formatDate(date) {
  if (!date) return '-'
  return new Date(date).toLocaleDateString()
}

function triggerImport() {
  fileInput.value?.click()
}

async function onFileSelected(event) {
  const file = event.target.files[0]
  if (!file) return
  try {
    const result = await api.importModelLifecycles(file)
    toast.add({ severity: 'success', summary: t('common.messages.success'), detail: `${result.data.created} records imported`, life: 3000 })
    if (result.data.errors?.length) {
      toast.add({ severity: 'warn', summary: t('common.messages.warning'), detail: `${result.data.errors.length} errors`, life: 5000 })
    }
    fetchLifecycles()
    fetchStats()
  } catch (err) {
    toast.add({ severity: 'error', summary: t('common.messages.error'), detail: t('common.messages.importError'), life: 3000 })
  }
  event.target.value = ''
}

function downloadTemplate() {
  const link = document.createElement('a')
  link.href = '/template_import_model_lifecycle.csv'
  link.download = 'template_import_model_lifecycle.csv'
  link.click()
}
</script>

<style scoped>
.model-lifecycles-page {
  padding: 1rem;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}
.header-actions {
  display: flex;
  gap: 0.5rem;
}
.stats-bar {
  display: flex;
  gap: 1rem;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
}
.stat-card {
  background: var(--surface-card);
  border: 1px solid var(--surface-border);
  border-radius: 8px;
  padding: 1rem 1.5rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 100px;
}
.stat-value {
  font-size: 1.5rem;
  font-weight: bold;
  color: var(--primary-color);
}
.stat-label {
  font-size: 0.8rem;
  color: var(--text-color-secondary);
  margin-top: 0.25rem;
}
.text-danger {
  color: #ef4444;
  font-weight: 600;
}
</style>
