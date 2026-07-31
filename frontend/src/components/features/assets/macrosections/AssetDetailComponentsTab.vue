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
          <label>{{ t('common.fields.notes') }}</label>
          <Textarea v-model="form.notes" :rows="3" class="w-full" />
        </div>
      </div>
      <template #footer>
        <Button :label="t('common.actions.cancel')" icon="pi pi-times" class="p-button-text" @click="closeDialog" />
        <Button :label="t('common.actions.save')" icon="pi pi-check" :loading="saving" @click="saveComponent" />
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useI18n } from 'vue-i18n'
import api from '../../../../api/api'

const props = defineProps({
  assetId: { type: String, required: true },
  canWrite: { type: Boolean, default: false }
})

const emit = defineEmits(['updated'])

const toast = useToast()
const { t } = useI18n()

const components = ref([])
const loading = ref(false)
const saving = ref(false)
const showAddDialog = ref(false)
const editingComponent = ref(null)
const modelOptions = ref([])

const form = ref({
  model_lifecycle_id: null,
  quantity: 1,
  notes: ''
})

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
    const res = await api.getModelLifecycles({ limit: 1000 })
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
  form.value = {
    model_lifecycle_id: comp.model_lifecycle_id,
    quantity: comp.quantity,
    notes: comp.notes || ''
  }
  showAddDialog.value = true
}

function closeDialog() {
  showAddDialog.value = false
  editingComponent.value = null
  form.value = { model_lifecycle_id: null, quantity: 1, notes: '' }
}

async function saveComponent() {
  saving.value = true
  try {
    if (editingComponent.value) {
      await api.put(`/assets/${props.assetId}/components/${editingComponent.value.id}`, form.value)
      toast.add({ severity: 'success', summary: t('common.messages.updated'), detail: t('assetComponents.updated'), life: 3000 })
    } else {
      await api.post(`/assets/${props.assetId}/components`, form.value)
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
