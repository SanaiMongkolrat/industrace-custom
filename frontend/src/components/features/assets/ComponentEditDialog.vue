<!--
  ComponentEditDialog.vue
  Shared add/edit dialog for an asset_component row.

  Used by:
    - AssetDetailComponentsTab.vue (inside Asset Detail page)
    - AssetLifecycleDashboard.vue   (inline edit from the fleet dashboard)

  Props:
    visible     v-model boolean
    component   component object to edit (null = add mode, requires assetId in add mode)
    assetId     required for both add and edit (PUT/POST target asset)
    assetInstallationDate  parent asset's install date (used as default when component has none)

  Emits:
    update:visible   v-model close
    saved            after successful save; payload = the API response row (or { componentId } for create)
-->
<template>
  <Dialog
    :visible="visible"
    @update:visible="$emit('update:visible', $event)"
    :header="isEdit ? t('common.actions.edit') : t('common.actions.add')"
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
          <span v-if="assetInstallationDate">{{ t('assetComponents.installationDateHintDefault', { date: formatDate(assetInstallationDate) }) }}</span>
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
      <Button :label="t('common.actions.save')" icon="pi pi-check" :loading="saving" @click="save" />
    </template>
  </Dialog>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useI18n } from 'vue-i18n'
import api from '../../../api/api'

import Dialog from 'primevue/dialog'
import Dropdown from 'primevue/dropdown'
import InputNumber from 'primevue/inputnumber'
import Calendar from 'primevue/calendar'
import Textarea from 'primevue/textarea'
import Button from 'primevue/button'

const props = defineProps({
  visible: { type: Boolean, required: true },
  component: { type: Object, default: null },
  assetId: { type: String, required: true },
  assetInstallationDate: { type: [String, Date], default: null },
})

const emit = defineEmits(['update:visible', 'saved'])

const toast = useToast()
const { t } = useI18n()

const saving = ref(false)
const modelOptions = ref([])
const locationOptions = ref([])

const isEdit = computed(() => !!props.component)

const form = ref(blankForm())

function blankForm() {
  const prefillDate = props.assetInstallationDate ? new Date(props.assetInstallationDate) : null
  return { model_lifecycle_id: null, quantity: 1, installation_date: prefillDate, notes: '', location_id: null }
}

function formatDate(value) {
  if (!value) return '-'
  const d = typeof value === 'string' ? new Date(value) : value
  if (isNaN(d)) return value
  return d.toISOString().slice(0, 10)
}

function resetForm() {
  if (props.component) {
    const existingDate = props.component.installation_date ? new Date(props.component.installation_date) : null
    const prefillDate = existingDate || (props.assetInstallationDate ? new Date(props.assetInstallationDate) : null)
    form.value = {
      model_lifecycle_id: props.component.model_lifecycle_id,
      quantity: props.component.quantity,
      installation_date: prefillDate,
      notes: props.component.notes || '',
      location_id: props.component.location_id || null,
    }
  } else {
    form.value = blankForm()
  }
}

watch(
  () => [props.visible, props.component, props.assetId],
  ([vis]) => {
    if (vis) {
      resetForm()
      // Lazy-load dropdowns (idempotent — keeps cache while dialog re-opens)
      if (!modelOptions.value.length) fetchModelOptions()
      if (!locationOptions.value.length) fetchLocationOptions()
    }
  },
  { immediate: true }
)

async function fetchModelOptions() {
  try {
    const res = await api.getModelLifecycles({ limit: 500 })
    modelOptions.value = (res.data || []).map((lc) => ({
      id: lc.id,
      label: `${lc.manufacturer_name || '?'} - ${lc.model_name}${lc.asset_type_name ? ' (' + lc.asset_type_name + ')' : ''}`,
    }))
  } catch (err) {
    toast.add({ severity: 'error', summary: t('common.messages.error'), detail: t('assetComponents.fetchModelOptionsError'), life: 3000 })
  }
}

async function fetchLocationOptions() {
  try {
    const res = await api.get('/locations', { params: { limit: 1000 } })
    locationOptions.value = (res.data || res.data?.items || []).map((loc) => ({
      id: loc.id,
      label: loc.code ? `${loc.name} (${loc.code})` : loc.name,
    }))
  } catch (err) {
    locationOptions.value = []
  }
}

function closeDialog() {
  emit('update:visible', false)
}

async function save() {
  saving.value = true
  try {
    const payload = {
      ...form.value,
      installation_date: form.value.installation_date
        ? typeof form.value.installation_date === 'string'
          ? form.value.installation_date
          : form.value.installation_date.toISOString().slice(0, 10)
        : null,
    }
    if (isEdit.value) {
      const res = await api.put(`/assets/${props.assetId}/components/${props.component.id}`, payload)
      toast.add({ severity: 'success', summary: t('common.messages.updated'), detail: t('assetComponents.updated'), life: 3000 })
      emit('saved', { mode: 'edit', data: res.data, componentId: props.component.id })
    } else {
      const res = await api.post(`/assets/${props.assetId}/components`, payload)
      toast.add({ severity: 'success', summary: t('common.messages.created'), detail: t('assetComponents.created'), life: 3000 })
      emit('saved', { mode: 'create', data: res.data })
    }
    closeDialog()
  } catch (err) {
    toast.add({ severity: 'error', summary: t('common.messages.error'), detail: t('assetComponents.saveError'), life: 3000 })
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.w-full { width: 100%; }
</style>
