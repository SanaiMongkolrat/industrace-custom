<template>
  <div class="asset-components-tab">
    <div class="flex justify-content-between align-items-center mb-3">
      <h3 class="m-0">{{ t('assetComponents.title') }}</h3>
      <Button
        v-if="canWrite"
        :label="t('common.actions.add')"
        icon="pi pi-plus"
        class="p-button-sm"
        @click="showAddDialog = true"
      />
      <Button
        v-if="canWrite && props.assetInstallationDate && nullComponentCount > 0"
        :label="t('assetComponents.bulkApplyAssetDate', { count: nullComponentCount })"
        icon="pi pi-calendar-clock"
        severity="secondary"
        class="p-button-sm"
        :loading="bulkApplying"
        @click="confirmBulkApply"
      />
    </div>

    <DataTable :value="components" :loading="loading" paginator :rows="10" :rowsPerPageOptions="[5, 10, 25]">
      <Column field="model_lifecycle_manufacturer_name" :header="t('common.fields.manufacturer')" sortable></Column>
      <Column field="model_lifecycle_model_name" :header="t('common.fields.model')" sortable></Column>
      <Column field="model_lifecycle_asset_type_name" :header="t('modelLifecycles.fields.assetType')" sortable></Column>
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
      <Column field="notes" :header="t('common.fields.notes')"></Column>
      <Column :header="t('common.strings.actions')" v-if="canWrite">
        <template #body="{ data }">
          <Button icon="pi pi-pencil" class="p-button-rounded p-button-text p-button-sm" @click="editComponent(data)" />
          <Button icon="pi pi-trash" class="p-button-rounded p-button-text p-button-danger p-button-sm" @click="deleteComponent(data.id)" />
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
const editingComponent = ref(null)
const modelOptions = ref([])

const form = ref({
  model_lifecycle_id: null,
  quantity: 1,
  installation_date: null,
  notes: ''
})

const nullComponentCount = computed(() => {
  return components.value.filter(c => !c.installation_date).length
})

function formatDate(value) {
  if (!value) return '-'
  // Backend returns ISO date string (YYYY-MM-DD) or Date object
  const d = typeof value === 'string' ? new Date(value) : value
  if (isNaN(d)) return value
  return d.toISOString().slice(0, 10)
}

function isInherited(comp) {
  // A component "inherits" its date from the parent asset when:
  // - It has no installation_date of its own, AND
  // - The parent asset has an installation_date
  if (!comp || comp.installation_date) return false
  if (!props.assetInstallationDate) return false
  return true
}

onMounted(() => {
  fetchComponents()
  fetchModelOptions()
})

async function fetchComponents() {
  loading.value = true
  try {
    const res = await api.get(`/assets/${props.assetId}/components`)
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
    // Silently fail
  }
}

function editComponent(comp) {
  editingComponent.value = comp
  // Prefill logic:
  // - If the component already has an installation_date set by the user, use it
  // - Otherwise, default to the parent asset's installation_date as a hint
  //   (user can clear it, override it, or save as-is — only their explicit
  //    choice is persisted)
  const existingDate = comp.installation_date ? new Date(comp.installation_date) : null
  const prefillDate = existingDate || (props.assetInstallationDate ? new Date(props.assetInstallationDate) : null)
  form.value = {
    model_lifecycle_id: comp.model_lifecycle_id,
    quantity: comp.quantity,
    installation_date: prefillDate,
    notes: comp.notes || ''
  }
  showAddDialog.value = true
}

function closeDialog() {
  showAddDialog.value = false
  editingComponent.value = null
  // On Add, also prefill from asset date so new components inherit by default
  const prefillDate = props.assetInstallationDate ? new Date(props.assetInstallationDate) : null
  form.value = { model_lifecycle_id: null, quantity: 1, installation_date: prefillDate, notes: '' }
}

async function saveComponent() {
  saving.value = true
  try {
    // Convert Date object from DatePicker to ISO YYYY-MM-DD string for the API
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
  if (!confirm(t('assetComponents.deleteConfirm'))) return
  try {
    await api.delete(`/assets/${props.assetId}/components/${id}`)
    toast.add({ severity: 'success', summary: t('common.messages.deleted'), detail: t('assetComponents.deleted'), life: 3000 })
    fetchComponents()
    emit('updated')
  } catch (err) {
    toast.add({ severity: 'error', summary: t('common.messages.error'), detail: t('assetComponents.deleteError'), life: 3000 })
  }
}

function confirmBulkApply() {
  showBulkConfirm.value = true
}

async function executeBulkApply() {
  bulkApplying.value = true
  try {
    // Empty body — backend will use the parent asset's installation_date
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
</style>
