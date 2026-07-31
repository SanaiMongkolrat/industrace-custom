<template>
  <form @submit.prevent="handleSubmit">
    <div class="p-fluid">
      <div class="p-field">
        <label for="manufacturer_id">{{ t('common.fields.manufacturer') }} <span class="required">*</span></label>
        <Dropdown id="manufacturer_id" v-model="form.manufacturer_id" :options="manufacturers" optionLabel="name" optionValue="id" :placeholder="t('common.strings.select')" :filter="true" required />
      </div>

      <div class="p-field">
        <label for="model_name">{{ t('common.fields.model') }} <span class="required">*</span></label>
        <InputText id="model_name" v-model="form.model_name" required />
      </div>

      <div class="p-field">
        <label for="asset_type_id">{{ t('modelLifecycles.fields.assetType') }}</label>
        <Dropdown id="asset_type_id" v-model="form.asset_type_id" :options="assetTypes" optionLabel="name" optionValue="id" :placeholder="t('common.strings.select')" :filter="true" :showClear="true" />
      </div>

      <div class="p-field">
        <label for="lifecycle_status">{{ t('modelLifecycles.fields.lifecycleStatus') }} <span class="required">*</span></label>
        <Dropdown id="lifecycle_status" v-model="form.lifecycle_status" :options="statusOptions" optionLabel="label" optionValue="value" :placeholder="t('common.strings.select')" required />
      </div>

      <div class="p-field">
        <label for="status_date">{{ t('modelLifecycles.fields.statusDate') }}</label>
        <Calendar id="status_date" v-model="form.status_date" dateFormat="yy-mm-dd" :showIcon="true" />
      </div>

      <div class="p-field">
        <label for="useful_life_years">{{ t('modelLifecycles.fields.usefulLifeYears') }}</label>
        <Dropdown id="useful_life_years" v-model="form.useful_life_years" :options="usefulLifeOptions" :placeholder="t('common.strings.select')" :showClear="true" />
      </div>

      <div class="p-field">
        <label for="end_of_support_date">{{ t('modelLifecycles.fields.eosDate') }}</label>
        <Calendar id="end_of_support_date" v-model="form.end_of_support_date" dateFormat="yy-mm-dd" :showIcon="true" />
      </div>

      <div class="p-field">
        <label for="spare_part_availability">{{ t('modelLifecycles.fields.spareParts') }}</label>
        <Dropdown id="spare_part_availability" v-model="form.spare_part_availability" :options="spareOptions" optionLabel="label" optionValue="value" :placeholder="t('common.strings.select')" />
      </div>

      <div class="p-field">
        <label for="replacement_model">{{ t('modelLifecycles.fields.replacement') }}</label>
        <InputText id="replacement_model" v-model="form.replacement_model" />
      </div>

      <div class="p-field">
        <label for="replacement_manufacturer_id">{{ t('modelLifecycles.fields.replacementManufacturer') }}</label>
        <Dropdown id="replacement_manufacturer_id" v-model="form.replacement_manufacturer_id" :options="manufacturers" optionLabel="name" optionValue="id" :placeholder="t('common.strings.select')" :showClear="true" />
      </div>

      <div class="p-field">
        <label for="notes">{{ t('common.fields.notes') }}</label>
        <Textarea id="notes" v-model="form.notes" autoResize />
      </div>

      <div class="p-field">
        <label for="last_reviewed_date">{{ t('modelLifecycles.fields.lastReviewed') }}</label>
        <Calendar id="last_reviewed_date" v-model="form.last_reviewed_date" dateFormat="yy-mm-dd" :showIcon="true" />
      </div>

      <div class="flex justify-content-end gap-2 mt-4">
        <Button :label="t('common.actions.cancel')" class="p-button-text" @click="emit('cancel')" />
        <Button :label="t('common.actions.save')" type="submit" />
      </div>
    </div>
  </form>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Button from 'primevue/button'
import Dropdown from 'primevue/dropdown'
import Calendar from 'primevue/calendar'
import api from '../../api/api'

const { t } = useI18n()

const props = defineProps({
  manufacturers: { type: Array, default: () => [] },
  lifecycle: { type: Object, default: null }
})

const emit = defineEmits(['submit', 'cancel'])

const assetTypes = ref([])

const form = ref({
  manufacturer_id: null,
  model_name: '',
  asset_type_id: null,
  lifecycle_status: 'in_support',
  status_date: null,
  useful_life_years: null,
  end_of_support_date: null,
  spare_part_availability: null,
  replacement_model: '',
  replacement_manufacturer_id: null,
  notes: '',
  last_reviewed_date: null
})

const usefulLifeOptions = [
  { value: 5, label: '5 Years' },
  { value: 10, label: '10 Years' },
  { value: 15, label: '15 Years' },
  { value: 20, label: '20 Years' },
  { value: 25, label: '25 Years' },
  { value: 30, label: '30 Years' }
]

const statusOptions = [
  { value: 'in_support', label: t('modelLifecycles.status.in_support') },
  { value: 'phase_out', label: t('modelLifecycles.status.phase_out') },
  { value: 'limited_support', label: t('modelLifecycles.status.limited_support') },
  { value: 'no_spare_parts', label: t('modelLifecycles.status.no_spare_parts') },
  { value: 'obsolete', label: t('modelLifecycles.status.obsolete') }
]

const spareOptions = [
  { value: 'available', label: t('modelLifecycles.spareParts.available') },
  { value: 'limited', label: t('modelLifecycles.spareParts.limited') },
  { value: 'unavailable', label: t('modelLifecycles.spareParts.unavailable') }
]

onMounted(async () => {
  try {
    const res = await api.getAssetTypes()
    assetTypes.value = res.data
  } catch (e) {
    // Silently fail
  }
})

watch(() => props.lifecycle, (newVal) => {
  if (newVal) {
    form.value = {
      manufacturer_id: newVal.manufacturer_id || null,
      model_name: newVal.model_name || '',
      asset_type_id: newVal.asset_type_id || null,
      lifecycle_status: newVal.lifecycle_status || 'in_support',
      status_date: newVal.status_date ? new Date(newVal.status_date) : null,
      useful_life_years: newVal.useful_life_years || null,
      end_of_support_date: newVal.end_of_support_date ? new Date(newVal.end_of_support_date) : null,
      spare_part_availability: newVal.spare_part_availability || null,
      replacement_model: newVal.replacement_model || '',
      replacement_manufacturer_id: newVal.replacement_manufacturer_id || null,
      notes: newVal.notes || '',
      last_reviewed_date: newVal.last_reviewed_date ? new Date(newVal.last_reviewed_date) : null
    }
  } else {
    form.value = {
      manufacturer_id: null,
      model_name: '',
      asset_type_id: null,
      lifecycle_status: 'in_support',
      status_date: null,
      useful_life_years: null,
      end_of_support_date: null,
      spare_part_availability: null,
      replacement_model: '',
      replacement_manufacturer_id: null,
      notes: '',
      last_reviewed_date: null
    }
  }
}, { immediate: true })

function handleSubmit() {
  const payload = { ...form.value }
  // Convert dates to ISO strings
  for (const key of ['status_date', 'end_of_support_date', 'last_reviewed_date']) {
    if (payload[key] instanceof Date) {
      payload[key] = payload[key].toISOString().split('T')[0]
    }
  }
  emit('submit', payload)
}
</script>

<style scoped>
.required {
  color: #dc3545;
  font-weight: bold;
}
.p-field {
  margin-bottom: 1rem;
}
.p-field label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
}
</style>
