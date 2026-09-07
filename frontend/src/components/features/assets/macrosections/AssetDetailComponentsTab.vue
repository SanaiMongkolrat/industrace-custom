<template>
  <div class="asset-components-tab">
    <div class="flex justify-content-between align-items-center mb-3">
      <h3 class="m-0">{{ t('assetComponents.title') }}</h3>
      <div class="flex gap-2 align-items-center">
        <Button
          v-if="canWrite && props.assetInstallationDate && nullComponentCount > 0"
          :label="t('assetComponents.bulkApplyAssetDate', { count: nullComponentCount })"
          icon="pi pi-calendar-clock"
          severity="secondary"
          class="p-button-sm"
          :loading="bulkApplying"
          @click="confirmBulkApply"
        />
        <Button
          v-if="canWrite"
          :label="t('common.actions.add')"
          icon="pi pi-plus"
          class="p-button-sm"
          @click="showAddDialog = true"
        />
      </div>
    </div>

    <DataTable :value="components" :loading="loading" paginator :rows="10" :rowsPerPageOptions="[5, 10, 25]">
      <Column field="model_lifecycle_manufacturer_name" :header="t('common.fields.manufacturer')" sortable></Column>
      <Column field="model_lifecycle_model_name" :header="t('common.fields.model')" sortable></Column>
      <Column field="model_lifecycle_asset_type_name" :header="t('modelLifecycles.fields.assetType')" sortable></Column>
      <Column field="location_name" :header="t('assetComponents.location')" sortable>
        <template #body="{ data }">
          <span v-if="data.location_name">{{ data.location_name }}</span>
          <span v-else class="text-muted">-</span>
        </template>
      </Column>
      <Column field="quantity" :header="t('assetComponents.quantity')" sortable>
        <template #body="{ data }">
          <Tag :value="data.quantity" severity="info" />
        </template>
      </Column>
      <Column field="model_lifecycle_lifecycle_status" :header="t('modelLifecycles.fields.lifecycleStatus')" sortable>
        <template #body="{ data }">
          <Tag :value="getStatusLabel(data.model_lifecycle_lifecycle_status)" :severity="getStatusSeverity(data.model_lifecycle_lifecycle_status)" />
        </template>
      </Column>
      <Column field="installation_date" :header="t('assetComponents.installationDate')" sortable>
        <template #body="{ data }">
          <div class="installation-date-cell">
            <span>{{ formatDate(data.installation_date) }}</span>
            <small v-if="isInherited(data)" class="text-muted">{{ t('assetComponents.installationDateInherited') }}</small>
          </div>
        </template>
      </Column>
      <Column field="lifespan_years" :header="t('assetComponents.lifespanYears')" sortable>
        <template #body="{ data }">
          <span v-if="data.lifespan_years !== null && data.lifespan_years !== undefined">{{ formatNumber(data.lifespan_years) }}</span>
          <span v-else class="text-muted">-</span>
        </template>
      </Column>
      <Column field="effective_useful_life" :header="t('assetComponents.usefulLife')" sortable>
        <template #body="{ data }">
          <div v-if="data.effective_useful_life !== null">
            <span>{{ data.effective_useful_life }}</span>
            <small class="text-muted d-block">{{ getUsefulLifeSourceLabel(data.useful_life_source) }}</small>
          </div>
          <span v-else class="text-muted">-</span>
        </template>
      </Column>
      <Column field="years_remaining" :header="t('assetComponents.yearsRemaining')" sortable>
        <template #body="{ data }">
          <span v-if="data.years_remaining !== null && data.years_remaining !== undefined"
                :class="data.years_remaining < 0 ? 'text-red-600 font-bold' : ''">
            {{ formatNumber(data.years_remaining) }}
          </span>
          <span v-else class="text-muted">-</span>
        </template>
      </Column>
      <Column field="lifecycle_status" :header="t('assetComponents.lifecycleStatus')" sortable>
        <template #body="{ data }">
          <Tag
            v-if="data.lifecycle_status"
            :value="getLifecycleStatusLabel(data.lifecycle_status)"
            :severity="getLifecycleStatusSeverity(data.lifecycle_status)"
          />
          <span v-else class="text-muted">-</span>
        </template>
      </Column>
      <Column field="notes" :header="t('common.fields.notes')"></Column>
      <Column :header="t('common.strings.actions')" v-if="canWrite">
        <template #body="{ data }">
          <Button icon="pi pi-pencil" :aria-label="t('common.actions.edit')" class="p-button-rounded p-button-text p-button-sm" @click="editComponent(data)" />
          <Button icon="pi pi-trash" :aria-label="t('common.actions.delete')" class="p-button-rounded p-button-text p-button-danger p-button-sm" @click="deleteComponent(data.id)" />
        </template>
      </Column>
    </DataTable>

    <div v-if="!components.length && !loading" class="text-center text-500 p-4">
      {{ t('assetComponents.noComponents') }}
    </div>

    <!-- Add/Edit Dialog -->
    <Dialog
      v-model:visible="showAddDialog"
      :header="editingComponent ? t('common.actions.edit') : t('common.actions.add')"
      :modal="true"
      :style="{ width: '500px' }"
    >
      <div class="p-fluid">
        <div class="field">
          <label>{{ t('assetComponents.selectModel') }}</label>
          <Dropdown
            v-model="form.model_lifecycle_id"
            :options="modelOptions"
            optionValue="id"
            optionLabel="label"
            :placeholder="t('assetComponents.selectModel')"
            :filter="true"
            class="w-full"
          />
        </div>
        <div class="field">
          <label>{{ t('assetComponents.quantity') }}</label>
          <InputNumber v-model="form.quantity" :min="1" class="w-full" />
        </div>
        <div class="field">
          <label>{{ t('assetComponents.location') }}</label>
          <Dropdown
            v-model="form.location_id"
            :options="locationOptions"
            optionValue="id"
            optionLabel="label"
            :placeholder="t('common.actions.select') || 'Select location'"
            :filter="true"
            :showClear="true"
            class="w-full"
          />
        </div>
        <div class="field">
          <label for="installation_date">{{ t('assetComponents.installationDate') }}</label>
          <Calendar id="installation_date" v-model="form.installation_date" dateFormat="yy-mm-dd" :showIcon="true" class="w-full" />
          <small class="text-muted">
            <span v-if="props.assetInstallationDate">{{ t('assetComponents.installationDateHintDefault', { date: formatDate(props.assetInstallationDate) }) }}</span>
            <span v-else>{{ t('assetComponents.installationDateHint') }}</span>
          </small>
        </div>
        <div class="field">
          <label>{{ t('common.fields.notes') }}</label>
          <Textarea v-model="form.notes" :rows="3" class="w-full" />
        </div>
      </div>
      <template #footer>
        <Button :label="t('common.actions.cancel')" icon="pi pi-times" class="p-button-text" @click="closeDialog" />
        <Button :label="t('common.actions.save')" icon="pi pi-check" :loading="saving" @click="saveComponent" />
      </template>
    </Dialog>

    <Dialog
      v-model:visible="showBulkConfirm"
      :header="t('assetComponents.bulkApplyTitle')"
      :modal="true"
      :style="{ width: '450px' }"
    >
      <div class="p-fluid">
        <p>{{ t('assetComponents.bulkApplyConfirmMessage', { count: nullComponentCount, date: formatDate(props.assetInstallationDate) }) }}</p>
        <p class="text-muted">{{ t('assetComponents.bulkApplyPreservesManual') }}</p>
      </div>
      <template #footer>
        <Button :label="t('common.actions.cancel')" icon="pi pi-times" class="p-button-text" @click="showBulkConfirm = false" />
        <Button :label="t('assetComponents.bulkApplyConfirm')" icon="pi pi-check" severity="warning" :loading="bulkApplying" @click="executeBulkApply" />
      </template>
    </Dialog>
    <!-- Delete Confirm Dialog -->
    <BaseConfirmDialog
      :showConfirmDialog="showDeleteConfirm"
      :confirmData="{ type: 'delete', message: t('assetComponents.deleteConfirm') }"
      @close="showDeleteConfirm = false"
      @execute="confirmDelete"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useI18n } from 'vue-i18n'
import api from '../../../../api/api'
import InputNumber from 'primevue/inputnumber'
import Textarea from 'primevue/textarea'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Dropdown from 'primevue/dropdown'
import Calendar from 'primevue/calendar'
import BaseConfirmDialog from '@/components/base/BaseConfirmDialog.vue'

const props = defineProps({
  assetId: { type: String, required: true },
  assetInstallationDate: { type: [String, Date], default: null },
  canWrite: { type: Boolean, default: false }
})

const emit = defineEmits(['updated'])

const toast = useToast()
const { t } = useI18n()

const components = ref([])
const loading = ref(false)
const saving = ref(false)
const bulkApplying = ref(false)
const showAddDialog = ref(false)
const showBulkConfirm = ref(false)
const showDeleteConfirm = ref(false)
const deleteTargetId = ref(null)
const editingComponent = ref(null)
const modelOptions = ref([])
const locationOptions = ref([])

const form = ref({
  model_lifecycle_id: null,
  quantity: 1,
  installation_date: null,
  notes: '',
  location_id: null
})

const nullComponentCount = computed(() => {
  return components.value.filter(c => !c.installation_date).length
})

function formatDate(value) {
  if (!value) return '-'
  const d = typeof value === 'string' ? new Date(value) : value
  if (isNaN(d)) return value
  return d.toISOString().slice(0, 10)
}

function formatNumber(value) {
  if (value === null || value === undefined) return '-'
  return Number(value).toFixed(2)
}

function isInherited(comp) {
  // A component "inherits" its date from the parent asset when:
  // - It has no installation_date of its own, AND
  // - The parent asset has an installation_date
  if (!comp || comp.installation_date) return false
  if (!props.assetInstallationDate) return false
  return true
}

function getStatusLabel(status) {
  const map = {
    'in_support': t('modelLifecycles.status.in_support'),
    'phase_out': t('modelLifecycles.status.phase_out'),
    'limited_support': t('modelLifecycles.status.limited_support'),
    'no_spare_parts': t('modelLifecycles.status.no_spare_parts'),
    'obsolete': t('modelLifecycles.status.obsolete'),
    'not_applicable': t('modelLifecycles.status.not_applicable'),
  }
  return map[status] || status
}

function getStatusSeverity(status) {
  const map = { 'in_support': 'success', 'phase_out': 'warn', 'limited_support': 'warn', 'no_spare_parts': 'danger', 'obsolete': 'danger', 'not_applicable': 'info' }
  return map[status] || 'info'
}

function getLifecycleStatusLabel(status) {
  const map = {
    'endOfLife': t('assetComponents.status.endOfLife'),
    'normal': t('assetComponents.status.normal'),
  }
  return map[status] || status
}

function getLifecycleStatusSeverity(status) {
  const map = { 'endOfLife': 'danger', 'normal': 'success' }
  return map[status] || 'info'
}

function getUsefulLifeSourceLabel(source) {
  const map = {
    'model': t('assetComponents.usefulLifeSourceModel'),
    'inherited_from_asset_type': t('assetComponents.usefulLifeSourceInherited'),
    'not_set': t('assetComponents.usefulLifeSourceNotSet'),
  }
  return map[source] || source
}

onMounted(() => {
  fetchComponents()
  fetchModelOptions()
  fetchLocationOptions()
})

async function fetchComponents() {
  loading.value = true
  try {
    // Use lifecycle-status endpoint to get computed columns
    const res = await api.get(`/assets/${props.assetId}/components/lifecycle-status`)
    components.value = res.data
  } catch (err) {
    toast.add({ severity: 'error', summary: t('common.messages.error'), detail: t('assetComponents.fetchError'), life: 3000 })
  } finally {
    loading.value = false
  }
}

async function fetchModelOptions() {
  try {
    const res = await api.getModelLifecycles({ limit: 500 })
    modelOptions.value = (res.data || []).map(lc => ({
      id: lc.id,
      label: `${lc.manufacturer_name || '?'} - ${lc.model_name}${lc.asset_type_name ? ' (' + lc.asset_type_name + ')' : ''}`
    }))
  } catch (err) {
    toast.add({ severity: 'error', summary: t('common.messages.error'), detail: t('assetComponents.fetchModelOptionsError'), life: 3000 })
  }
}

async function fetchLocationOptions() {
  try {
    const res = await api.get('/locations', { params: { limit: 1000 } })
    locationOptions.value = (res.data || res.data?.items || []).map(loc => ({
      id: loc.id,
      label: loc.code ? `${loc.name} (${loc.code})` : loc.name
    }))
  } catch (err) {
    // Non-fatal: the location dropdown just stays empty
    locationOptions.value = []
  }
}

function editComponent(comp) {
  editingComponent.value = comp
  const existingDate = comp.installation_date ? new Date(comp.installation_date) : null
  const prefillDate = existingDate || (props.assetInstallationDate ? new Date(props.assetInstallationDate) : null)
  form.value = {
    model_lifecycle_id: comp.model_lifecycle_id,
    quantity: comp.quantity,
    installation_date: prefillDate,
    notes: comp.notes || '',
    location_id: comp.location_id || null
  }
  showAddDialog.value = true
}

function closeDialog() {
  showAddDialog.value = false
  editingComponent.value = null
  const prefillDate = props.assetInstallationDate ? new Date(props.assetInstallationDate) : null
  form.value = { model_lifecycle_id: null, quantity: 1, installation_date: prefillDate, notes: '', location_id: null }
}

async function saveComponent() {
  saving.value = true
  try {
    const payload = {
      ...form.value,
      installation_date: form.value.installation_date
        ? (typeof form.value.installation_date === 'string'
            ? form.value.installation_date
            : form.value.installation_date.toISOString().slice(0, 10))
        : null
    }
    if (editingComponent.value) {
      await api.put(`/assets/${props.assetId}/components/${editingComponent.value.id}`, payload)
      toast.add({ severity: 'success', summary: t('common.messages.updated'), detail: t('assetComponents.updated'), life: 3000 })
    } else {
      await api.post(`/assets/${props.assetId}/components`, payload)
      toast.add({ severity: 'success', summary: t('common.messages.created'), detail: t('assetComponents.created'), life: 3000 })
    }
    closeDialog()
    fetchComponents()
    emit('updated')
  } catch (err) {
    toast.add({ severity: 'error', summary: t('common.messages.error'), detail: t('assetComponents.saveError'), life: 3000 })
  } finally {
    saving.value = false
  }
}

async function deleteComponent(id) {
  deleteTargetId.value = id
  showDeleteConfirm.value = true
}

async function confirmDelete() {
  if (!deleteTargetId.value) return
  try {
    await api.delete(`/assets/${props.assetId}/components/${deleteTargetId.value}`)
    toast.add({ severity: 'success', summary: t('common.messages.deleted'), detail: t('assetComponents.deleted'), life: 3000 })
    fetchComponents()
    emit('updated')
  } catch (err) {
    toast.add({ severity: 'error', summary: t('common.messages.error'), detail: t('assetComponents.deleteError'), life: 3000 })
  } finally {
    showDeleteConfirm.value = false
    deleteTargetId.value = null
  }
}

function confirmBulkApply() {
  showBulkConfirm.value = true
}

async function executeBulkApply() {
  bulkApplying.value = true
  try {
    const res = await api.post(`/assets/${props.assetId}/components/apply-asset-date`, {})
    const count = res.data?.updated_count ?? 0
    const date = res.data?.installation_date ?? ''
    if (count > 0) {
      toast.add({
        severity: 'success',
        summary: t('assetComponents.bulkApplyDone'),
        detail: t('assetComponents.bulkApplyDoneDetail', { count, date }),
        life: 5000
      })
    } else {
      toast.add({
        severity: 'info',
        summary: t('assetComponents.bulkApplyNothing'),
        life: 3000
      })
    }
    showBulkConfirm.value = false
    fetchComponents()
    emit('updated')
  } catch (err) {
    toast.add({ severity: 'error', summary: t('common.messages.error'), detail: t('assetComponents.bulkApplyError'), life: 5000 })
  } finally {
    bulkApplying.value = false
  }
}
</script>

<style scoped>
.installation-date-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.installation-date-cell small {
  font-size: 0.75rem;
  font-style: italic;
}
.text-red-600 {
  color: #dc2626;
}
.font-bold {
  font-weight: 600;
}
.d-block {
  display: block;
}
</style>
